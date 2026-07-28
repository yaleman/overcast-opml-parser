"""Parser/munger for Overcast OPML files"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from requests_xml import XML, Element


class Playlist(BaseModel):
    """playlist def"""

    title: str
    smart: bool
    sorting: (
        str  # probably should be an enum, since I'm sure there's only a few options
    )
    includePodcastIds: list[int] | None = Field(None)
    includeEpisodeIds: list[int] | None = Field(None)
    sortedEpisodeIds: list[int] | None = Field(None)


class Episode(BaseModel):
    """episode object"""

    overcastId: int
    pubDate: datetime
    title: str
    url: str
    enclosureUrl: str
    overcastUrl: str
    progress: int = 0
    userUpdatedDate: datetime
    userDeleted: bool = False
    played: bool = False
    userRecommendedDate: datetime | None = Field(None)


class Feed(BaseModel):
    """feed object"""

    overcastId: int
    title: str
    xmlUrl: str | None = Field(None)
    htmlUrl: str | None = Field(None)
    subscribed: bool = Field(False)
    episodes: list[Episode] = Field([])


class OPMLFile(BaseModel):
    """type def for the data returned from load_file"""

    playlists: list[Playlist] = Field([])
    feeds: list[Feed] = Field([])


def xpath_first_element(root: XML | Element, selector: str) -> Element | None:
    """Return the first XML element for selectors known to target elements."""
    return cast(Element | None, root.xpath(selector, first=True))


def xpath_elements(root: XML | Element, selector: str) -> list[Element]:
    """Return XML elements for selectors known to target elements."""
    return cast(list[Element], root.xpath(selector))


def load_file(filename: Path, check_unhandled_attr: bool = False) -> XML:
    """loads the file and parses it with untangle"""

    with filename.expanduser().resolve().open(encoding="utf8") as file_handle:
        filecontents = file_handle.readlines()

    xmldata = XML(xml="".join(filecontents[1:]))
    return xmldata


def parse(xmldata: XML, check_unhandled_attr: bool) -> OPMLFile:
    playlists = xpath_first_element(xmldata, "//outline[@text='playlists']")

    if playlists is None:
        logger.error(
            "Couldn't find playlists (looking for //outline[@text='playlists'])",
        )
        sys.exit(1)

    feeds = xpath_first_element(xmldata, "//outline[@text='feeds']")
    if feeds is None:
        logger.error(
            "Couldn't find feeds (looking for //outline[@text='feeds'])",
        )
        sys.exit(1)

    retval = OPMLFile(playlists=[], feeds=[])

    unhandled_feed_attr: list[str] = []
    ignore_feed_attr = ["type", "text"]

    unhandled_playlist_attr: list[str] = []
    ignore_playlist_attr = ["text", "type"]

    unhandled_episode_attr: list[str] = []
    ignore_episode_attr = ["text", "type"]

    playlist_elements = xpath_elements(playlists, "//outline[@type='podcast-playlist']")
    if not playlist_elements:
        logger.error("Couldn't find playlists")
        sys.exit(1)

    for playlist in playlist_elements:
        for key in ["includePodcastIds", "includeEpisodeIds", "sortedEpisodeIds"]:
            if key in playlist.attrs:
                playlist.attrs[key] = [int(el) for el in playlist.attrs[key].split(",")]
        playlist_object = Playlist(**playlist.attrs)
        if check_unhandled_attr:
            for attr in playlist.attrs:
                if (
                    attr not in ignore_playlist_attr
                    and attr not in unhandled_playlist_attr
                    and not hasattr(playlist_object, attr)
                ):
                    unhandled_playlist_attr.append(attr)
        retval.playlists.append(playlist_object)

    for feed in xpath_elements(feeds, "//outline[@type='rss']"):
        try:
            feed_object = Feed(**feed.attrs)
            if check_unhandled_attr:
                for attr in feed.attrs:
                    if (
                        attr not in unhandled_feed_attr
                        and attr not in ignore_feed_attr
                        and not hasattr(feed_object, attr)
                    ):
                        unhandled_feed_attr.append(attr)
        except ValidationError as error_message:
            logger.error(error_message)
            logger.error(json.dumps(feed, default=str))

        episodes = xpath_elements(feed, "//outline[@type='podcast-episode']")
        for episode in episodes:
            try:
                episode_object = Episode(**episode.attrs)
                feed_object.episodes.append(episode_object)

                if check_unhandled_attr:
                    for attr in episode.attrs:
                        if (
                            attr not in unhandled_episode_attr
                            and attr not in ignore_episode_attr
                            and not hasattr(episode_object, attr)
                        ):
                            unhandled_episode_attr.append(attr)
            except ValidationError as error_message:
                logger.error(error_message)
                logger.error(json.dumps(episode, default=str))

        retval.feeds.append(feed_object)
    if check_unhandled_attr:
        if unhandled_playlist_attr:
            logger.warning(
                "Need to parse the following 'playlist' attrs: {}",
                unhandled_playlist_attr,
            )
        if unhandled_feed_attr:
            logger.warning(
                "Need to parse the following 'feed' attrs: {}", unhandled_feed_attr
            )
        if unhandled_episode_attr:
            logger.warning(
                "Need to parse the following 'episode' attrs: {}",
                unhandled_episode_attr,
            )

    return retval

#!/usr/bin/env python3
"""parses the "All data" OPML file from
https://overcast.fm/account and shows some simple stats
"""

# import os.path
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Optional, cast


from loguru import logger
from requests_xml import Element, XML
import click
from pydantic import BaseModel, Field, ValidationError


class Playlist(BaseModel):
    """playlist def"""

    title: str
    smart: bool
    sorting: (
        str  # probably should be an enum, since I'm sure there's only a few options
    )
    includePodcastIds: Optional[list[int]] = Field(None)
    includeEpisodeIds: Optional[list[int]] = Field(None)
    sortedEpisodeIds: Optional[list[int]] = Field(None)


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
    userRecommendedDate: Optional[datetime] = Field(None)


class Feed(BaseModel):
    """feed object"""

    overcastId: int
    title: str
    xmlUrl: Optional[str] = Field(None)
    htmlUrl: Optional[str] = Field(None)
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


def load_file(filename: Path, check_unhandled_attr: bool = False) -> OPMLFile:
    """loads the file and parses it with untangle"""
    if not filename.exists():
        return OPMLFile(playlists=[], feeds=[])

    with filename.expanduser().resolve().open(encoding="utf8") as file_handle:
        filecontents = file_handle.readlines()

    xmldata = XML(xml="".join(filecontents[1:]))
    playlists = xpath_first_element(xmldata, "//outline[@text='playlists']")

    if playlists is None:
        logger.error(
            "Couldn't find playlists in {} (looking for //outline[@text='playlists'])",
            filename,
        )
        sys.exit(1)

    feeds = xpath_first_element(xmldata, "//outline[@text='feeds']")
    if feeds is None:
        logger.error(
            "Couldn't find feeds in {} (looking for //outline[@text='feeds'])",
            filename,
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
        logger.error("Couldn't find playlists in {}", filename)
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


@click.command()
@click.argument("filename", type=click.File())
def cli(filename: Optional[click.File] = None) -> None:
    """Overcast.fm Extended OPML Parser"""

    if filename is None:
        return
    filepath = Path(filename.name).expanduser().resolve()
    if not filepath.exists():
        print(f"File {filepath} doesn't exist, bailing", file=sys.stderr)
        return
    data = load_file(filepath, check_unhandled_attr=True)
    print(data.model_dump_json(indent=4))


if __name__ == "__main__":
    cli()

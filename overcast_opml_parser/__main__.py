#!/usr/bin/env python3
""" parses the "All data" OPML file from
    https://overcast.fm/account and shows some simple stats
    """

# import os.path
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Optional


from loguru import logger
from requests_xml import XML
import click
from pydantic import BaseModel, Field, ValidationError


class Playlist(BaseModel):
    """playlist def"""

    title: str
    smart: bool
    sorting: str  # probably should be an enum, since I'm sure there's only a few options
    includePodcastIds: Optional[List[int]] = Field(None)
    includeEpisodeIds: Optional[List[int]] = Field(None)
    sortedEpisodeIds: Optional[List[int]] = Field(None)


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
    episodes: List[Episode] = Field([])


class OPMLFile(BaseModel):
    """type def for the data returned from load_file"""

    playlists: List[Playlist] = Field([])
    feeds: List[Feed] = Field([])


def load_file(filename: Path, check_unhandled_attr: bool = False) -> OPMLFile:
    """loads the file and parses it with untangle"""
    if not filename.exists():
        return OPMLFile()

    with filename.expanduser().resolve().open(encoding="utf8") as file_handle:
        filecontents = file_handle.readlines()

    xmldata = XML(xml="".join(filecontents[1:]))
    playlists = xmldata.xpath("//outline[@text='playlists']", first=True)

    if playlists is None:
        logger.error(
            "Couldn't find playlists in {} (looking for //outline[@text='playlists'])",
            filename,
        )
        sys.exit(1)

    feeds = xmldata.xpath("//outline[@text='feeds']", first=True)

    retval = OPMLFile()

    unhandled_feed_attr: List[str] = []
    ignore_feed_attr = ["type", "text"]

    unhandled_playlist_attr: List[str] = []
    ignore_playlist_attr = ["text", "type"]

    unhandled_episode_attr: List[str] = []
    ignore_episode_attr = ["text", "type"]

    playlists_xpath = playlists.xpath("//outline[@type='podcast-playlist']")
    if playlists_xpath is None:
        logger.error("Couldn't find playlists in {}", filename)
        sys.exit(1)

    for playlist in playlists_xpath:
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

    for feed in feeds.xpath("//outline[@type='rss']"):
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

        episodes = feed.xpath("//outline[@type='podcast-episode']")
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
def cli(filename: click.File = None) -> None:
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

import pytest
from pathlib import Path
from overcast_opml_parser import load_file, parse


def test_no_playlists():
    data = load_file(Path("tests/fixtures/no_playlists.opml"))
    with pytest.raises(SystemExit):
        parse(data, check_unhandled_attr=False)
    with pytest.raises(SystemExit):
        parse(data, check_unhandled_attr=True)


def test_no_feeds():
    data = load_file(Path("tests/fixtures/no_feeds.opml"))
    with pytest.raises(SystemExit):
        parse(data, check_unhandled_attr=False)
    with pytest.raises(SystemExit):
        parse(data, check_unhandled_attr=True)

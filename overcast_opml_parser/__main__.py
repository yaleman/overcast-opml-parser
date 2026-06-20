#!/usr/bin/env python3
"""parses the "All data" OPML file from
https://overcast.fm/account and shows some simple stats
"""

# import os.path

from pathlib import Path
from overcast_opml_parser import load_file, parse
import click


@click.command()
@click.argument("filename", type=click.File())
def cli(filename: click.File) -> None:
    """Overcast.fm Extended OPML Parser"""

    filepath = Path(filename.name).expanduser().resolve()
    data = load_file(filepath, check_unhandled_attr=True)
    opml = parse(data, check_unhandled_attr=True)
    print(opml.model_dump_json(indent=4))


if __name__ == "__main__":
    cli()  # pragma: no cover

#!/usr/bin/env python3
"""parses the "All data" OPML file from
https://overcast.fm/account and shows some simple stats
"""

# import os.path

import sys
from pathlib import Path
from overcast_opml_parser import load_file
from typing import Optional
import click


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

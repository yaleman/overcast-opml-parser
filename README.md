# overcast-opml-parser

[![PyPI](https://img.shields.io/pypi/v/overcast-opml-parser.svg)](https://pypi.org/project/overcast-opml-parser/)

A parser for Overcast's extended format

## Installation

Install this library using `pip`:

    $ python -m pip install overcast-opml-parser

## Usage

Usage instructions go here.

## Development

To contribute to this library, first checkout the code. Then install the development environment with `uv`:

    cd overcast-opml-parser
    uv sync --dev

Run the checks locally with:

    uv run ruff check overcast_opml_parser tests
    uv run ty check overcast_opml_parser tests
    uv run pytest

"""Dumper plugin system for STANG.

New output formats can be added by subclassing :class:`Dumper` and registering
it in :data:`DUMPERS`.
"""

from __future__ import annotations

from stang.dumpers.base import Dumper
from stang.dumpers.block import BlockDumper
from stang.dumpers.csv import CSVDumper
from stang.dumpers.json import JSONDumper
from stang.dumpers.markdown import MarkdownDumper
from stang.dumpers.ndjson import NDJSONDumper
from stang.dumpers.raw import RawDumper
from stang.dumpers.stats import StatsDumper
from stang.dumpers.tsv import TSVDumper

DUMPERS: dict[str, type[Dumper]] = {
    "default": BlockDumper,
    "block": BlockDumper,
    "json": JSONDumper,
    "ndjson": NDJSONDumper,
    "csv": CSVDumper,
    "tsv": TSVDumper,
    "markdown": MarkdownDumper,
    "md": MarkdownDumper,
    "stats": StatsDumper,
    "raw": RawDumper,
}

__all__ = [
    "BlockDumper",
    "CSVDumper",
    "DUMPERS",
    "Dumper",
    "JSONDumper",
    "MarkdownDumper",
    "NDJSONDumper",
    "RawDumper",
    "StatsDumper",
    "TSVDumper",
]

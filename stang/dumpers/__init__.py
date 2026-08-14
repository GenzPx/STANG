"""Dumper plugin system for STANG.

New output formats can be added by subclassing :class:`Dumper` and registering
it in :data:`DUMPERS`.
"""

from __future__ import annotations

from typing import ClassVar

from stang.container import STGContainer


class Dumper:
    """Base class for STANG output formatters."""

    name: ClassVar[str] = "base"

    def dump(self, container: STGContainer) -> str:
        """Return a string representation of *container*."""
        raise NotImplementedError


# Import concrete dumpers so they can be discovered.
from stang.dumpers.block import BlockDumper
from stang.dumpers.csv import CSVDumper
from stang.dumpers.json import JSONDumper
from stang.dumpers.raw import RawDumper

DUMPERS: dict[str, type[Dumper]] = {
    "default": BlockDumper,
    "block": BlockDumper,
    "json": JSONDumper,
    "csv": CSVDumper,
    "raw": RawDumper,
}

__all__ = ["Dumper", "DUMPERS", "BlockDumper", "CSVDumper", "JSONDumper", "RawDumper"]

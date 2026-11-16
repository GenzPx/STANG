"""Base class for STANG dumper plugins."""

from __future__ import annotations

from typing import ClassVar

from stang.container import STGContainer


class Dumper:
    """Base class for STANG output formatters."""

    name: ClassVar[str] = "base"

    def dump(self, container: STGContainer) -> str:
        """Return a string representation of *container*."""
        raise NotImplementedError

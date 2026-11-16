"""JSON dumper plugin."""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers.base import Dumper


class JSONDumper(Dumper):
    """Dump container records as pretty-printed JSON."""

    name = "json"

    def dump(self, container: STGContainer) -> str:
        """Render records as pretty-printed JSON."""
        records = decode_stg(container)
        return json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True)

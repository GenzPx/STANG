"""NDJSON dumper plugin."""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers.base import Dumper


class NDJSONDumper(Dumper):
    """Dump one JSON record per line (newline-delimited JSON)."""

    name = "ndjson"

    def dump(self, container: STGContainer) -> str:
        """Render records as newline-delimited JSON."""
        records = decode_stg(container)
        return "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            for record in records
        )

"""STG decoder: .stg container -> structured data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stang.blocks import merge_blocks
from stang.container import STGContainer


def decode_stg(container: STGContainer) -> list[dict[str, Any]]:
    """Decode a container back to its original list of records.

    The decoder normalizes the rotation state by merging blocks in their
    canonical storage order. This guarantees ``decode(encode(data)) == data``
    semantically.
    """
    return merge_blocks(container.blocks)


def load_stg(path: str | Path) -> list[dict[str, Any]]:
    """Load and decode a ``.stg`` file from disk."""
    data = Path(path).read_bytes()
    container = STGContainer.deserialize(data)
    return decode_stg(container)


def decode_to_json(container: STGContainer) -> bytes:
    """Decode a container to a deterministic JSON byte payload."""
    records = decode_stg(container)
    return json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )

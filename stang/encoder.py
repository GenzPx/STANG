"""STG encoder: structured data -> .stg container."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from stang.blocks import partition_records
from stang.container import STGContainer
from stang.schema import Schema

DEFAULT_BLOCK_COUNT = 4


def encode_stg(
    records: Sequence[Mapping[str, Any]],
    block_count: int = DEFAULT_BLOCK_COUNT,
    rotation_state: int = 0,
    flags: int = 0,
) -> STGContainer:
    """Encode structured records into a :class:`STGContainer`.

    Parameters
    ----------
    records:
        Sequence of JSON-compatible record mappings.
    block_count:
        Number of rotational blocks to create. Must be positive.
    rotation_state:
        Initial logical rotation state.
    flags:
        Reserved container flags.

    Returns
    -------
    STGContainer
        A fully constructed in-memory container.
    """
    if block_count <= 0:
        raise ValueError("block_count must be positive")
    if not records:
        schema = Schema({})
    else:
        # Infer schema from all records, merging fields.
        merged: dict[str, Any] = {}
        for record in records:
            merged.update(record)
        schema = Schema.infer(merged)

    blocks = partition_records(records, block_count)
    return STGContainer(schema, blocks, rotation_state=rotation_state, flags=flags)


def save_stg(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
    block_count: int = DEFAULT_BLOCK_COUNT,
    rotation_state: int = 0,
    flags: int = 0,
) -> None:
    """Encode *records* and write the resulting STG file to *path*."""
    container = encode_stg(records, block_count, rotation_state, flags)
    Path(path).write_bytes(container.serialize())


def encode_from_json(data: bytes, block_count: int = DEFAULT_BLOCK_COUNT) -> STGContainer:
    """Encode from a raw JSON byte payload.

    Accepts either a single object (treated as one record) or an array of
    objects.
    """
    parsed = json.loads(data.decode("utf-8"))
    if isinstance(parsed, dict):
        records = [parsed]
    elif isinstance(parsed, list):
        records = parsed
    else:
        raise ValueError("JSON payload must be an object or an array of objects")
    return encode_stg(records, block_count)

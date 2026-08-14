"""Block partitioning logic for STG containers.

A block is the atomic storage unit inside a container. Records are distributed
across blocks deterministically so that encode/decode round-trips are stable.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def partition_records(records: Sequence[Any], block_count: int) -> list[list[Any]]:
    """Distribute *records* evenly across *block_count* blocks.

    Distribution is round-robin by record index to keep the layout stable and
trivially reversible. Empty containers still create the requested number of
empty blocks so the rotational model remains well-defined.
    """
    if block_count <= 0:
        raise ValueError("block_count must be positive")
    blocks: list[list[Any]] = [[] for _ in range(block_count)]
    for index, record in enumerate(records):
        blocks[index % block_count].append(record)
    return blocks


def merge_blocks(blocks: Sequence[Sequence[Any]]) -> list[Any]:
    """Reassemble records from round-robin blocks.

    This is the inverse of :func:`partition_records` when block order is the
    canonical (non-rotated) order.
    """
    if not blocks:
        return []
    result: list[Any] = []
    max_len = max(len(block) for block in blocks) if blocks else 0
    for offset in range(max_len):
        for block in blocks:
            if offset < len(block):
                result.append(block[offset])
    return result

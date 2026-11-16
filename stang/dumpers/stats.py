"""Statistics dumper plugin.

Shows how records are distributed across the rotational blocks — useful for
inspecting the physical layout of a container without decoding the payload.
"""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.dumpers.base import Dumper


def _byte_len(value: object) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )


class StatsDumper(Dumper):
    """Dump per-block statistics for the container's blocks."""

    name = "stats"

    def dump(self, container: STGContainer) -> str:
        """Render a per-block distribution table."""
        total_records = container.record_count
        total_bytes = sum(_byte_len(list(block)) for block in container.blocks)
        lines = [
            f"STANG STATS — STG{container.format_version}",
            f"records={total_records} blocks={container.block_count} "
            f"rotation={container.rotation_state} payload_json_bytes={total_bytes}",
            "",
            f"{'BLOCK':<7}{'RECORDS':<9}{'BYTES':<8}{'SHARE':<7}ROTATION",
        ]
        for index, block in enumerate(container.blocks):
            block_bytes = _byte_len(list(block))
            share = (len(block) / total_records * 100) if total_records else 0.0
            marker = "  <-- current" if index == container.rotation_state else ""
            lines.append(
                f"{index:<7}{len(block):<9}{block_bytes:<8}{share:5.1f}% {marker}".rstrip()
            )
        return "\n".join(lines)

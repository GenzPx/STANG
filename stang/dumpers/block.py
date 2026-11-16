"""Default block-oriented dumper."""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.dumpers.base import Dumper


class BlockDumper(Dumper):
    """Dump a human-readable overview plus each block."""

    name = "block"

    def dump(self, container: STGContainer) -> str:
        """Render a human-readable block listing."""
        flags = []
        if container.is_compressed:
            flags.append("compressed")
        if container.is_encrypted:
            flags.append("encrypted")
        lines = [
            "STANG DUMP",
            "==========",
            "",
            f"Format     : STG{container.format_version}",
            f"Version    : {container.version}",
            f"Flags      : {', '.join(flags) if flags else 'none'}",
            f"Blocks     : {container.block_count}",
            f"Rotation   : {container.rotation_state}",
            f"Records    : {sum(len(block) for block in container.blocks)}",
            f"Schema     : {container.schema.fields}",
            "",
        ]
        for index, block in enumerate(container.blocks):
            label = f"[BLOCK {index}]"
            if index == container.rotation_state:
                label += "  <-- current"
            lines.append(label)
            for record in block:
                lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
            lines.append("")
        return "\n".join(lines).rstrip()

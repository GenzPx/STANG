"""Default block-oriented dumper."""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.dumpers import Dumper


class BlockDumper(Dumper):
    """Dump a human-readable overview plus each block."""

    name = "block"

    def dump(self, container: STGContainer) -> str:
        lines = [
            "STANG DUMP",
            "==========",
            "",
            f"Version    : {container.version}",
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

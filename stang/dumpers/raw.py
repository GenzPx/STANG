"""Raw internal structure dumper plugin."""

from __future__ import annotations

import json

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers.base import Dumper


class RawDumper(Dumper):
    """Dump the internal, logical structure of a container for debugging."""

    name = "raw"

    def dump(self, container: STGContainer) -> str:
        """Render the internal logical structure as JSON."""
        canonical = decode_stg(container)
        rotated_blocks = (
            list(container.blocks[container.rotation_state :])
            + list(container.blocks[: container.rotation_state])
        )
        rotated_view = [list(block) for block in rotated_blocks]
        structure = {
            "magic": container.magic.decode("ascii"),
            "version": container.version,
            "format": f"STG{container.format_version}",
            "flags": container.flags,
            "compressed": container.is_compressed,
            "encrypted": container.is_encrypted,
            "rotation_state": container.rotation_state,
            "block_count": container.block_count,
            "schema": container.schema.to_dict(),
            "canonical_records": canonical,
            "rotated_view": rotated_view,
            "blocks": [list(block) for block in container.blocks],
        }
        return json.dumps(structure, ensure_ascii=False, indent=2, sort_keys=True)

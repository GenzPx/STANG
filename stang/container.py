"""In-memory representation of a STG container."""

from __future__ import annotations

import json
import struct
from collections.abc import Sequence
from typing import Any

from stang.checksum import container_checksum, verify_checksum
from stang.schema import Schema

MAGIC = b"STG1"
VERSION = 1
HEADER_FMT = "!4sBBII"  # magic, version, flags, rotation_state, schema_len
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class ContainerError(ValueError):
    """Raised when container operations fail."""


class STGContainer:
    """In-memory STG container.

    A container consists of:

    * a magic identifier and version
    * flags (reserved for future extensibility)
    * a rotational state
    * a schema describing the data
    * a table of block offsets/sizes
    * the data blocks themselves
    * a trailing checksum

    The container does not enforce a fixed block count; callers decide the
    number of blocks when encoding.
    """

    def __init__(
        self,
        schema: Schema,
        blocks: Sequence[Sequence[Any]],
        rotation_state: int = 0,
        flags: int = 0,
    ) -> None:
        self.schema = schema
        self.blocks = tuple(tuple(block) for block in blocks)
        self.block_count = len(self.blocks)
        if self.block_count == 0:
            raise ContainerError("STG container must contain at least one block.")
        self.rotation_state = rotation_state % self.block_count
        self.flags = flags

    @property
    def version(self) -> int:
        return VERSION

    @property
    def magic(self) -> bytes:
        return MAGIC

    def serialize_payload(self) -> bytes:
        """Serialize everything except the trailing checksum."""
        schema_bytes = json.dumps(
            self.schema.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

        block_bytes_list: list[bytes] = []
        for block in self.blocks:
            block_bytes_list.append(
                json.dumps(
                    list(block), ensure_ascii=False, separators=(",", ":"), sort_keys=True
                ).encode("utf-8")
            )

        table, table_bytes = self._compute_table(block_bytes_list, schema_bytes)

        header = struct.pack(
            HEADER_FMT,
            self.magic,
            self.version,
            self.flags,
            self.rotation_state,
            len(schema_bytes),
        )

        parts = [header, schema_bytes, table_bytes]
        parts.extend(block_bytes_list)
        return b"".join(parts)

    @staticmethod
    def _compute_table(
        block_bytes_list: Sequence[bytes], schema_bytes: bytes
    ) -> tuple[list[list[int]], bytes]:
        """Compute the block table and its serialized form.

        Offsets are absolute from the start of the payload. Because the table
        length depends on the offsets written inside it, we converge on a
        stable solution iteratively.
        """
        start = HEADER_SIZE + len(schema_bytes)
        table_bytes = json.dumps(
            [[0, len(b)] for b in block_bytes_list], separators=(",", ":")
        ).encode("utf-8")
        while True:
            offset = start + len(table_bytes)
            table: list[list[int]] = []
            for block_bytes in block_bytes_list:
                table.append([offset, len(block_bytes)])
                offset += len(block_bytes)
            new_table_bytes = json.dumps(table, separators=(",", ":")).encode("utf-8")
            if len(new_table_bytes) == len(table_bytes):
                return table, new_table_bytes
            table_bytes = new_table_bytes

    def serialize(self) -> bytes:
        """Serialize the full container including checksum."""
        payload = self.serialize_payload()
        checksum = container_checksum(self)
        return payload + checksum

    @classmethod
    def deserialize(cls, data: bytes) -> "STGContainer":
        """Deserialize a container and validate its checksum."""
        if len(data) < HEADER_SIZE + 32:
            raise ContainerError("File too short to be a valid STG container.")

        checksum_offset = len(data) - 32
        payload = data[:checksum_offset]
        expected_checksum = data[checksum_offset:]

        header = data[:HEADER_SIZE]
        magic, version, flags, rotation_state, schema_len = struct.unpack(HEADER_FMT, header)

        if magic != MAGIC:
            raise ContainerError(f"Invalid magic bytes: expected {MAGIC!r}, got {magic!r}")
        if version != VERSION:
            raise ContainerError(f"Unsupported STG version: {version}")

        if not verify_checksum(payload, expected_checksum):
            raise ContainerError("Checksum mismatch: container may be corrupted.")

        schema_start = HEADER_SIZE
        schema_end = schema_start + schema_len
        schema_bytes = data[schema_start:schema_end]
        try:
            schema = Schema.from_dict(json.loads(schema_bytes.decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ContainerError("Failed to parse schema") from exc

        # Table length is implicit: it occupies the bytes between the schema and
        # the first block described by the table. The first block offset is the
        # first entry of the table, so we parse the table incrementally.
        table_start = schema_end
        table_decoder = json.JSONDecoder()
        try:
            table, _ = table_decoder.raw_decode(payload[table_start:].decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ContainerError("Failed to parse block table") from exc

        blocks: list[list[Any]] = []
        for block_offset, block_size in table:
            if block_offset + block_size > len(payload):
                raise ContainerError("Block table points outside payload bounds.")
            block_data = payload[block_offset : block_offset + block_size]
            try:
                blocks.append(json.loads(block_data.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ContainerError("Failed to parse data block") from exc

        return cls(schema, blocks, rotation_state=rotation_state, flags=flags)

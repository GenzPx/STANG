"""In-memory representation of an STG container.

Supports two wire formats:

* **STG1** (legacy, ``MAGIC_V1``): 14-byte header, embedded absolute-offset
  block table, 32-byte SHA-256 trailer. Read and written for backward
  compatibility.
* **STG2** (current, ``MAGIC_V2``): 32-byte header, JSON header extension
  (schema and KDF parameters), length-prefixed block entries, optional
  zlib compression and authenticated encryption, variable trailer digest.

Both formats are auto-detected on :meth:`STGContainer.deserialize`.
"""

from __future__ import annotations

import hmac
import json
import secrets
import struct
import zlib
from collections.abc import Sequence
from typing import Any

from stang.checksum import normalize_key, verify_checksum
from stang.crypto import NONCE_SIZE, decrypt_block, derive_keys, encrypt_block
from stang.errors import AuthenticationError, ContainerError, EncryptionError, IntegrityError

__all__ = [
    "FLAG_COMPRESSED",
    "FLAG_ENCRYPTED",
    "FLAG_HMAC",
    "HEADER_FMT",
    "HEADER_SIZE",
    "MAGIC",
    "MAGIC_V1",
    "MAGIC_V2",
    "VERSION",
    "VERSION_V1",
    "VERSION_V2",
    "V2_HEADER_FMT",
    "V2_HEADER_SIZE",
    "ContainerError",
    "STGContainer",
]
from stang.schema import Schema

MAGIC_V1 = b"STG1"
MAGIC_V2 = b"STG2"
MAGIC = MAGIC_V1  # Backward-compatible alias for the v1 magic identifier.
VERSION_V1 = 1
VERSION_V2 = 2
VERSION = VERSION_V1  # Backward-compatible alias.

HEADER_FMT = "!4sBBII"  # v1: magic, version, flags, rotation_state, schema_len
HEADER_SIZE = struct.calcsize(HEADER_FMT)

V2_HEADER_FMT = "!4sBBIIH16s"  # magic, version, flags, rotation_state, ext_len, block_count, salt
V2_HEADER_SIZE = struct.calcsize(V2_HEADER_FMT)  # 32
V2_KDF_NAME = "pbkdf2-sha256"
V2_KDF_ITERATIONS = 100_000
V2_KDF_KEY_LEN = 64
V2_MAX_EXT_LEN = 4 * 1024 * 1024  # 4 MiB cap on the header extension
V2_MAX_BLOCKS = 0xFFFF

FLAG_COMPRESSED = 0x01
FLAG_ENCRYPTED = 0x02
FLAG_HMAC = 0x04

KDF_METADATA = {
    "name": V2_KDF_NAME,
    "iterations": V2_KDF_ITERATIONS,
    "key_len": V2_KDF_KEY_LEN,
}


KNOWN_FLAG_BITS = FLAG_COMPRESSED | FLAG_ENCRYPTED | FLAG_HMAC


def _reject_constant(value: str) -> Any:
    """Fail on NaN/Infinity literals, which are not valid JSON."""
    raise ContainerError(f"Non-finite number literal {value!r} is not allowed in STG containers.")


def _loads_strict(text: str) -> Any:
    """Parse JSON, rejecting NaN/Infinity constants (superset-of-JSON extensions)."""
    return json.loads(text, parse_constant=_reject_constant)


def _canonical_json(obj: Any) -> bytes:
    """Serialize a JSON-compatible object with deterministic key ordering.

    Raises ``ValueError`` when ``obj`` contains non-finite floats instead of
    emitting non-standard ``NaN``/``Infinity`` literals.
    """
    return json.dumps(
        obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode("utf-8")


class STGContainer:
    """In-memory STG container.

    A container consists of:

    * a magic identifier and format version
    * flags describing optional payload features
    * a rotational state (logical, never physical)
    * a schema describing the data
    * one or more data blocks
    * a trailing digest (SHA-256, or HMAC-SHA256 when keyed/encrypted)

    The container does not enforce a fixed block count; callers decide the
    number of blocks when encoding. Secrets (``passphrase`` / ``integrity_key``)
    are kept on the instance only to make re-serialization (e.g. after
    ``rotate``) seamless, are never written to disk, and are excluded from
    ``repr()``.
    """

    def __init__(
        self,
        schema: Schema,
        blocks: Sequence[Sequence[Any]],
        rotation_state: int = 0,
        flags: int = 0,
        *,
        passphrase: str | bytes | None = None,
        integrity_key: bytes | str | None = None,
        format_version: int = VERSION_V2,
    ) -> None:
        """Construct a container from a schema and block sequences."""
        if format_version not in (VERSION_V1, VERSION_V2):
            raise ContainerError(f"Unsupported STG format version: {format_version}")
        self.schema = schema
        self.blocks = tuple(tuple(block) for block in blocks)
        self.block_count = len(self.blocks)
        if self.block_count == 0:
            raise ContainerError("STG container must contain at least one block.")
        if self.block_count > V2_MAX_BLOCKS:
            raise ContainerError(f"STG container supports at most {V2_MAX_BLOCKS} blocks.")
        self.rotation_state = rotation_state % self.block_count
        if format_version == VERSION_V1:
            if flags != 0:
                raise ContainerError(f"Invalid STG1 flags: expected 0, got {flags:#04x}.")
        elif flags & ~KNOWN_FLAG_BITS:
            raise ContainerError(f"Invalid flags: unknown bits set in {flags:#04x}.")
        if (flags & FLAG_ENCRYPTED and flags & FLAG_HMAC) and format_version == VERSION_V2:
            raise ContainerError("Invalid flags: encryption already authenticates the payload.")
        self.flags = flags
        self.format_version = format_version
        self.salt: bytes = secrets.token_bytes(16) if self.flags & FLAG_ENCRYPTED else b"\x00" * 16
        self._passphrase = passphrase
        self._integrity_key = normalize_key(integrity_key)
        self._mac_key_cache: bytes | None = None

    # ------------------------------------------------------------------ #
    # Convenience accessors                                               #
    # ------------------------------------------------------------------ #

    @property
    def version(self) -> int:
        """Wire-format version this container serializes to."""
        return self.format_version

    @property
    def magic(self) -> bytes:
        """Magic identifier for the current wire format."""
        return MAGIC_V2 if self.format_version == VERSION_V2 else MAGIC_V1

    @property
    def is_compressed(self) -> bool:
        """True when block payloads are zlib-compressed."""
        return bool(self.flags & FLAG_COMPRESSED)

    @property
    def is_encrypted(self) -> bool:
        """True when block payloads are encrypted."""
        return bool(self.flags & FLAG_ENCRYPTED)

    @property
    def record_count(self) -> int:
        """Total number of records stored across all blocks."""
        return sum(len(block) for block in self.blocks)

    @property
    def requires_passphrase(self) -> bool:
        """True when reading/writing this container needs a passphrase."""
        return bool(self.flags & FLAG_ENCRYPTED)

    # ------------------------------------------------------------------ #
    # Serialization                                                       #
    # ------------------------------------------------------------------ #

    def serialize_payload(
        self,
        passphrase: str | bytes | None = None,
        integrity_key: bytes | str | None = None,
        *,
        salt: bytes | None = None,
        block_nonces: Sequence[bytes] | None = None,
    ) -> bytes:
        """Serialize everything except the trailing digest.

        Args:
            passphrase: Overrides the instance passphrase when set.
            integrity_key: Overrides the instance integrity key when set.
            salt: Advanced/testing hook — pin the 16-byte PBKDF2 salt.
            block_nonces: Advanced/testing hook — pin per-block 16-byte nonces.
        """
        if self.format_version == VERSION_V1:
            return self._serialize_payload_v1()
        return self._serialize_payload_v2(
            passphrase=passphrase,
            integrity_key=integrity_key,
            salt=salt,
            block_nonces=block_nonces,
        )

    def serialize(
        self,
        passphrase: str | bytes | None = None,
        integrity_key: bytes | str | None = None,
        *,
        salt: bytes | None = None,
        block_nonces: Sequence[bytes] | None = None,
    ) -> bytes:
        """Serialize the full container including the trailing digest."""
        payload = self.serialize_payload(
            passphrase, integrity_key, salt=salt, block_nonces=block_nonces
        )
        return payload + self._trailer(payload, passphrase, integrity_key)

    def _trailer(
        self,
        payload: bytes,
        passphrase: str | bytes | None,
        integrity_key: bytes | str | None,
    ) -> bytes:
        from stang.checksum import compute_checksum

        if self.format_version == VERSION_V1:
            return compute_checksum(payload, None)
        if self.flags & FLAG_ENCRYPTED:
            cached = getattr(self, "_mac_key_cache", None)
            if cached is not None:
                self._mac_key_cache = None
                return compute_checksum(payload, cached)
            pass_bytes = self._resolve_passphrase(passphrase)
            raw_pass = pass_bytes.encode("utf-8") if isinstance(pass_bytes, str) else pass_bytes
            _, mac_key = derive_keys(raw_pass, digest_salt(payload))
            return compute_checksum(payload, mac_key)
        key = self._resolve_integrity_key(integrity_key)
        return compute_checksum(payload, key)

    # ........................ v1 (legacy) path ........................ #

    def _serialize_payload_v1(self) -> bytes:
        schema_bytes = _canonical_json(self.schema.to_dict())
        block_bytes_list = [_canonical_json(list(block)) for block in self.blocks]
        table_bytes = self._compute_table(block_bytes_list, schema_bytes)
        header = struct.pack(
            HEADER_FMT,
            MAGIC_V1,
            VERSION_V1,
            self.flags & 0xFF,
            self.rotation_state,
            len(schema_bytes),
        )
        return b"".join([header, schema_bytes, table_bytes, *block_bytes_list])

    @staticmethod
    def _compute_table(
        block_bytes_list: Sequence[bytes], schema_bytes: bytes
    ) -> bytes:
        """Compute the v1 block table and its serialized form.

        Offsets are absolute from the start of the payload. Because the table
        length depends on the offsets written inside it, we converge on a
        stable solution iteratively.
        """
        start = HEADER_SIZE + len(schema_bytes)
        table_bytes = _canonical_json([[0, len(b)] for b in block_bytes_list])
        while True:
            offset = start + len(table_bytes)
            table: list[list[int]] = []
            for block_bytes in block_bytes_list:
                table.append([offset, len(block_bytes)])
                offset += len(block_bytes)
            new_table_bytes = _canonical_json(table)
            if len(new_table_bytes) == len(table_bytes):
                return new_table_bytes
            table_bytes = new_table_bytes

    # ........................ v2 path ................................. #

    def _resolve_passphrase(self, passphrase: str | bytes | None) -> bytes | str:
        resolved = passphrase if passphrase is not None else self._passphrase
        if resolved is None:
            raise EncryptionError(
                "This container is encrypted. Supply a passphrase "
                "(serialize(passphrase=...), --passphrase-env, or prompt)."
            )
        return resolved

    def _resolve_integrity_key(self, integrity_key: bytes | str | None) -> bytes | None:
        if integrity_key is not None:
            resolved = normalize_key(integrity_key)
        else:
            resolved = self._integrity_key
        if self.flags & FLAG_HMAC and resolved is None:
            raise EncryptionError(
                "This container requires an integrity key "
                "(serialize(integrity_key=...), --key-env, or --key-file)."
            )
        return resolved

    def _header_extension(self) -> dict[str, Any]:
        extension: dict[str, Any] = {"schema": self.schema.to_dict()}
        if self.flags & FLAG_ENCRYPTED:
            extension["kdf"] = dict(KDF_METADATA)
        return extension

    def _serialize_payload_v2(
        self,
        passphrase: str | bytes | None,
        integrity_key: bytes | str | None,
        salt: bytes | None,
        block_nonces: Sequence[bytes] | None,
    ) -> bytes:
        if self.flags & FLAG_ENCRYPTED and self.flags & FLAG_HMAC:
            raise EncryptionError("FLAG_ENCRYPTED already authenticates; drop FLAG_HMAC.")
        key = self._resolve_integrity_key(integrity_key)
        del key  # HMAC key is only needed for the trailer, not the payload.

        actual_salt = salt if salt is not None else self.salt
        if len(actual_salt) != NONCE_SIZE:
            raise EncryptionError(f"Salt must be {NONCE_SIZE} bytes.")
        self.salt = actual_salt

        ext_bytes = _canonical_json(self._header_extension())
        if len(ext_bytes) > V2_MAX_EXT_LEN:
            raise ContainerError("Header extension exceeds the 4 MiB limit.")

        # Derive encryption keys once when needed.
        enc_master: bytes | None = None
        if self.flags & FLAG_ENCRYPTED:
            pass_bytes = self._resolve_passphrase(passphrase)
            raw_pass = pass_bytes.encode("utf-8") if isinstance(pass_bytes, str) else pass_bytes
            if not raw_pass:
                raise EncryptionError("Encryption passphrase must not be empty.")
            enc_master, self._mac_key_cache = derive_keys(raw_pass, actual_salt)

        if block_nonces is not None and len(block_nonces) != self.block_count:
            raise EncryptionError("block_nonces must match the number of blocks.")

        header = struct.pack(
            V2_HEADER_FMT,
            MAGIC_V2,
            VERSION_V2,
            self.flags & 0xFF,
            self.rotation_state,
            len(ext_bytes),
            self.block_count,
            actual_salt,
        )

        parts = [header, ext_bytes]
        for index, block in enumerate(self.blocks):
            plaintext = _canonical_json(list(block))
            if self.flags & FLAG_COMPRESSED:
                plaintext = zlib.compress(plaintext, level=9)
            if enc_master is not None:
                nonce = block_nonces[index] if block_nonces is not None else None
                blob = encrypt_block(plaintext, enc_master, index, nonce)
            else:
                blob = plaintext
            parts.append(struct.pack("!I", len(blob)))
            parts.append(blob)
        return b"".join(parts)

    # ------------------------------------------------------------------ #
    # Deserialization                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def deserialize(
        cls,
        data: bytes,
        *,
        passphrase: str | bytes | None = None,
        integrity_key: bytes | str | None = None,
    ) -> STGContainer:
        """Deserialize a container of either format version.

        Args:
            data: Raw ``.stg`` file bytes.
            passphrase: Required when the container is encrypted (v2).
            integrity_key: Required when the container uses HMAC integrity (v2).

        Raises:
            ContainerError: On malformed input, digest mismatch, or bad credentials.
        """
        if len(data) < HEADER_SIZE + 32:
            raise ContainerError("File too short to be a valid STG container.")
        magic = data[:4]
        if magic == MAGIC_V1:
            return cls._deserialize_v1(data)
        if magic == MAGIC_V2:
            return cls._deserialize_v2(data, passphrase=passphrase, integrity_key=integrity_key)
        raise ContainerError(f"Invalid magic bytes: expected STG1 or STG2, got {magic!r}")

    @classmethod
    def _deserialize_v1(cls, data: bytes) -> STGContainer:
        if len(data) < HEADER_SIZE + 32:
            raise ContainerError("File too short to be a valid STG container.")
        checksum_offset = len(data) - 32
        payload, expected_checksum = data[:checksum_offset], data[checksum_offset:]
        magic, version, flags, rotation_state, schema_len = struct.unpack(
            HEADER_FMT, data[:HEADER_SIZE]
        )
        if magic != MAGIC_V1:  # pragma: no cover - guarded by caller
            raise ContainerError(f"Invalid magic bytes: expected {MAGIC_V1!r}, got {magic!r}")
        if version != VERSION_V1:
            raise ContainerError(f"Unsupported STG version: {version}")
        if flags != 0:
            raise ContainerError(f"Invalid STG1 flags: expected 0, got {flags:#04x}.")
        if not verify_checksum(payload, expected_checksum):
            raise ContainerError("Checksum mismatch: container may be corrupted.")

        schema_start = HEADER_SIZE
        schema_end = schema_start + schema_len
        schema_bytes = data[schema_start:schema_end]
        if schema_end > len(payload):
            raise ContainerError("Schema length points outside the payload.")
        try:
            schema = Schema.from_dict(_loads_strict(schema_bytes.decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError, ContainerError) as exc:
            raise ContainerError("Failed to parse schema") from exc

        table_start = schema_end
        table_decoder = json.JSONDecoder(parse_constant=_reject_constant)
        try:
            table, _ = table_decoder.raw_decode(payload[table_start:].decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ContainerError) as exc:
            raise ContainerError("Failed to parse block table") from exc
        if not isinstance(table, list):
            raise ContainerError("Block table must be a JSON array.")

        blocks: list[list[Any]] = []
        for entry in table:
            try:
                block_offset, block_size = int(entry[0]), int(entry[1])
            except (TypeError, IndexError, ValueError) as exc:
                raise ContainerError("Block table entries must be [offset, size] pairs.") from exc
            if block_offset < 0 or block_size < 0 or block_offset + block_size > len(payload):
                raise ContainerError("Block table points outside payload bounds.")
            block_data = payload[block_offset : block_offset + block_size]
            try:
                block = _loads_strict(block_data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, ContainerError) as exc:
                raise ContainerError("Failed to parse data block") from exc
            if not isinstance(block, list):
                raise ContainerError("Data block must decode to a JSON array.")
            blocks.append(block)

        return cls._from_parsed(schema, blocks, rotation_state, flags, VERSION_V1, None, None)

    @classmethod
    def _deserialize_v2(
        cls,
        data: bytes,
        *,
        passphrase: str | bytes | None,
        integrity_key: bytes | str | None,
    ) -> STGContainer:
        if len(data) < V2_HEADER_SIZE + 32:
            raise ContainerError("File too short to be a valid STG2 container.")
        magic, version, flags, rotation_state, ext_len, block_count, salt = struct.unpack(
            V2_HEADER_FMT, data[:V2_HEADER_SIZE]
        )
        if magic != MAGIC_V2:  # pragma: no cover - guarded by caller
            raise ContainerError(f"Invalid magic bytes: expected {MAGIC_V2!r}, got {magic!r}")
        if version != VERSION_V2:
            raise ContainerError(f"Unsupported STG version: {version}")
        if ext_len > V2_MAX_EXT_LEN:
            raise ContainerError("Header extension exceeds the 4 MiB limit.")
        if flags & ~KNOWN_FLAG_BITS:
            raise ContainerError(f"Invalid flags: unknown bits set in {flags:#04x}.")
        if flags & FLAG_ENCRYPTED and flags & FLAG_HMAC:
            raise ContainerError("Invalid flags: encryption already authenticates the payload.")

        checksum_offset = len(data) - 32
        payload, expected_trailer = data[:checksum_offset], data[checksum_offset:]

        # Derive keys / resolve credentials before touching any payload bytes.
        enc_master: bytes | None = None
        mac_key: bytes | None = None
        if flags & FLAG_ENCRYPTED:
            if passphrase is None:
                raise AuthenticationError(
                    "Container is encrypted. Supply a passphrase to read it."
                )
            raw_pass = passphrase.encode("utf-8") if isinstance(passphrase, str) else passphrase
            if not raw_pass:
                raise AuthenticationError("Encryption passphrase must not be empty.")
            enc_master, mac_key = derive_keys(raw_pass, salt)

        key = normalize_key(integrity_key)
        if flags & FLAG_HMAC and key is None:
            raise IntegrityError("Container requires an integrity key to be verified.")

        _verify_trailer(payload, expected_trailer, flags, mac_key, key)

        ext_start = V2_HEADER_SIZE
        ext_end = ext_start + ext_len
        if ext_end > len(payload):
            raise ContainerError("Header extension points outside the payload.")
        ext_bytes = payload[ext_start:ext_end]
        try:
            extension = _loads_strict(ext_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ContainerError) as exc:
            raise ContainerError("Failed to parse header extension") from exc
        if not isinstance(extension, dict):
            raise ContainerError("Header extension must be a JSON object.")
        schema_data = extension.get("schema", {"fields": {}})
        if not isinstance(schema_data, dict):
            raise ContainerError("Header extension 'schema' entry must be an object.")
        try:
            schema = Schema.from_dict(schema_data)
        except ValueError as exc:
            raise ContainerError("Failed to parse schema in header extension") from exc

        blocks: list[list[Any]] = []
        offset = ext_end
        for index in range(block_count):
            if offset + 4 > len(payload):
                raise ContainerError("Unexpected end of container while reading block header.")
            (blob_len,) = struct.unpack_from("!I", payload, offset)
            offset += 4
            if blob_len > len(payload) - offset:
                raise ContainerError("Block length points outside the payload.")
            blob = payload[offset : offset + blob_len]
            offset += blob_len
            if enc_master is not None:
                try:
                    plaintext = decrypt_block(blob, enc_master, index)
                except ValueError as exc:
                    raise ContainerError(f"Failed to decrypt block {index}") from exc
            else:
                plaintext = blob
            if flags & FLAG_COMPRESSED:
                try:
                    plaintext = zlib.decompress(plaintext)
                except zlib.error as exc:
                    raise ContainerError(f"Failed to decompress block {index}") from exc
            try:
                block = _loads_strict(plaintext.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, ContainerError) as exc:
                raise ContainerError(f"Failed to parse data block {index}") from exc
            if not isinstance(block, list):
                raise ContainerError(f"Data block {index} must decode to a JSON array.")
            blocks.append(block)

        if offset != len(payload):
            raise ContainerError("Trailing bytes after last block (container is malformed).")

        return cls._from_parsed(
            schema,
            blocks,
            rotation_state,
            flags,
            VERSION_V2,
            passphrase if flags & FLAG_ENCRYPTED else None,
            key if flags & FLAG_HMAC else None,
            salt=salt,
        )

    @classmethod
    def _from_parsed(
        cls,
        schema: Schema,
        blocks: list[list[Any]],
        rotation_state: int,
        flags: int,
        format_version: int,
        passphrase: str | bytes | None,
        integrity_key: bytes | None,
        salt: bytes | None = None,
    ) -> STGContainer:
        container = cls(
            schema,
            blocks,
            rotation_state=rotation_state,
            flags=flags,
            passphrase=passphrase,
            integrity_key=integrity_key,
            format_version=format_version,
        )
        if salt is not None:
            container.salt = salt
        return container

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def rotated_records_order(self) -> list[tuple[int, int]]:
        """Return ``(block_index, intra_block_offset)`` pairs in logical order."""
        indices = list(range(self.block_count))
        ordered = indices[self.rotation_state :] + indices[: self.rotation_state]
        pairs: list[tuple[int, int]] = []
        max_len = max((len(block) for block in self.blocks), default=0)
        for intra in range(max_len):
            for block_index in ordered:
                if intra < len(self.blocks[block_index]):
                    pairs.append((block_index, intra))
        return pairs

    def describe(self) -> dict[str, Any]:
        """Return a machine-readable summary of the container (no secrets)."""
        return {
            "format": f"STG{self.format_version}",
            "version": self.format_version,
            "flags": self.flags,
            "compressed": self.is_compressed,
            "encrypted": self.is_encrypted,
            "hmac": bool(self.flags & FLAG_HMAC),
            "rotation_state": self.rotation_state,
            "block_count": self.block_count,
            "record_count": self.record_count,
            "schema": self.schema.to_dict(),
        }

    def __repr__(self) -> str:
        """Return a secret-free developer summary."""
        return (
            f"{self.__class__.__name__}("
            f"format=STG{self.format_version}, blocks={self.block_count}, "
            f"records={self.record_count}, rotation={self.rotation_state}, "
            f"flags={self.flags})"
        )


def digest_salt(payload: bytes) -> bytes:
    """Extract the PBKDF2 salt embedded in an STG2 payload header."""
    return payload[16:32]


def _verify_trailer(
    payload: bytes,
    expected: bytes,
    flags: int,
    mac_key: bytes | None,
    integrity_key: bytes | None,
) -> None:
    from stang.checksum import compute_checksum

    if flags & FLAG_ENCRYPTED:
        if mac_key is None:  # pragma: no cover - guarded by caller
            raise AuthenticationError("Encrypted container is missing its MAC key.")
        actual = compute_checksum(payload, mac_key)
        if not hmac.compare_digest(actual, expected):
            raise AuthenticationError(
                "Authentication failed: wrong passphrase or corrupted data."
            )
        return
    if flags & FLAG_HMAC:
        if integrity_key is None:  # pragma: no cover - guarded by caller
            raise IntegrityError("Container requires an integrity key.")
        actual = compute_checksum(payload, integrity_key)
        if not hmac.compare_digest(actual, expected):
            raise IntegrityError("Integrity check failed: bad key or corrupted data.")
        return
    if not verify_checksum(payload, expected):
        raise ContainerError("Checksum mismatch: container may be corrupted.")

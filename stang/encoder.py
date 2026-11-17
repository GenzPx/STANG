"""STG encoder: structured data -> .stg container."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from stang.blocks import partition_records
from stang.container import (
    FLAG_COMPRESSED,
    FLAG_ENCRYPTED,
    FLAG_HMAC,
    VERSION_V2,
    STGContainer,
)
from stang.errors import ContainerError
from stang.schema import Schema

DEFAULT_BLOCK_COUNT = 4


def _reject_constant(value: str) -> Any:
    """Fail on NaN/Infinity literals, which are not valid JSON."""
    raise ContainerError(f"Non-finite number literal {value!r} is not allowed in JSON.")




def encode_stg(
    records: Sequence[Mapping[str, Any]],
    block_count: int = DEFAULT_BLOCK_COUNT,
    rotation_state: int = 0,
    flags: int = 0,
    *,
    passphrase: str | bytes | None = None,
    integrity_key: bytes | str | None = None,
    compress: bool = False,
    format_version: int = VERSION_V2,
    validate: bool = False,
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
        Explicit flag override. When ``compress=True`` is also passed,
        :data:`stang.container.FLAG_COMPRESSED` is OR-ed in automatically.
    passphrase:
        Encrypt block payloads (implies PBKDF2 key derivation +
        Encrypt-then-MAC). Requires format version 2.
    integrity_key:
        Candidate integrity key. When set and no passphrase is given, the
        container trailer becomes HMAC-SHA256 over the payload.
    compress:
        zlib-compress each block payload before (optional) encryption.
    format_version:
        Wire format to write: ``2`` (default) or ``1`` (legacy).
    validate:
        Validate every record against the inferred schema.

    Returns:
    -------
    STGContainer
        A fully constructed in-memory container.
    """
    if block_count <= 0:
        raise ValueError("block_count must be positive")
    if passphrase is not None and integrity_key is not None:
        raise ValueError("Pass either passphrase (encryption) or integrity_key (HMAC), not both.")
    record_list = list(records)
    for record in record_list:
        if not isinstance(record, Mapping):
            raise TypeError(f"Records must be mappings, got {type(record).__name__}.")

    schema = Schema.infer_many(record_list) if record_list else Schema({})
    if validate:
        for record in record_list:
            schema.validate_record(record, allow_extra=True)

    effective_flags = flags
    if compress:
        effective_flags |= FLAG_COMPRESSED
    if passphrase is not None:
        effective_flags |= FLAG_ENCRYPTED
    elif integrity_key is not None:
        effective_flags |= FLAG_HMAC

    if format_version == 1 and (effective_flags & (FLAG_COMPRESSED | FLAG_ENCRYPTED | FLAG_HMAC)):
        raise ValueError("Format version 1 does not support compression, encryption or HMAC.")

    blocks = partition_records(record_list, block_count)
    return STGContainer(
        schema,
        blocks,
        rotation_state=rotation_state,
        flags=effective_flags,
        passphrase=passphrase,
        integrity_key=integrity_key,
        format_version=format_version,
    )


def save_stg(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
    block_count: int = DEFAULT_BLOCK_COUNT,
    rotation_state: int = 0,
    flags: int = 0,
    *,
    passphrase: str | bytes | None = None,
    integrity_key: bytes | str | None = None,
    compress: bool = False,
    format_version: int = VERSION_V2,
    validate: bool = False,
) -> None:
    """Encode *records* and write the resulting STG file to *path*."""
    container = encode_stg(
        records,
        block_count,
        rotation_state,
        flags,
        passphrase=passphrase,
        integrity_key=integrity_key,
        compress=compress,
        format_version=format_version,
        validate=validate,
    )
    Path(path).write_bytes(container.serialize())


def _parse_ndjson(text: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON: one JSON object per line."""
    records: list[dict[str, Any]] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line, parse_constant=_reject_constant)
        except (json.JSONDecodeError, ContainerError) as exc:
            raise ValueError(f"NDJSON line {lineno} is not valid JSON: {exc}") from exc
        if not isinstance(item, Mapping):
            kind = type(item).__name__
            raise ValueError(f"NDJSON line {lineno} must be a JSON object, got {kind}.")
        records.append(dict(item))
    return records


def encode_from_json(
    data: bytes,
    block_count: int = DEFAULT_BLOCK_COUNT,
    *,
    passphrase: str | bytes | None = None,
    integrity_key: bytes | str | None = None,
    compress: bool = False,
    format_version: int = VERSION_V2,
    input_format: str = "json",
) -> STGContainer:
    """Encode from a raw JSON byte payload.

    With ``input_format="json"`` (default), accepts either a single object
    (treated as one record) or an array of objects. With ``input_format="ndjson"``,
    expects newline-delimited JSON objects (blank lines and lines starting with
    ``#`` are ignored).
    """
    text = data.decode("utf-8", errors="strict") if isinstance(data, bytes) else data
    try:
        if input_format == "ndjson":
            records: list[dict[str, Any]] = _parse_ndjson(text)
        else:
            try:
                parsed = json.loads(text, parse_constant=_reject_constant)
            except (json.JSONDecodeError, ContainerError) as exc:
                raise ValueError(f"Input is not valid JSON: {exc}") from exc
            if isinstance(parsed, dict):
                records = [parsed]
            elif isinstance(parsed, list):
                if not all(isinstance(item, Mapping) for item in parsed):
                    raise ValueError("JSON array must contain only objects.")
                records = [dict(item) for item in parsed]
            else:
                raise ValueError("JSON payload must be an object or an array of objects")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input is not valid UTF-8: {exc}") from exc
    return encode_stg(
        records,
        block_count,
        passphrase=passphrase,
        integrity_key=integrity_key,
        compress=compress,
        format_version=format_version,
    )


__all__ = [
    "DEFAULT_BLOCK_COUNT",
    "encode_from_json",
    "encode_stg",
    "save_stg",
]

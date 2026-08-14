# STANG File Format Specification

## Version

This document describes STG format version **1**.

## Overview

A `.stg` file is a self-describing, versioned, checksummed container for structured records. The format is intentionally simple and uses only standard-library-compatible serialization.

## Design Goals

- **Deterministic**: Same input and parameters produce identical bytes.
- **Versioned**: Tools can detect and reject unsupported format versions.
- **Extensible**: Header flags and a version field allow future extensions.
- **Integrity-checked**: A trailing checksum detects accidental corruption.
- **Round-trippable**: `decode(encode(data)) == data` semantically.

## File Layout

```text
┌─────────────────────────────────────┐
│ Header (fixed size)                 │
├─────────────────────────────────────┤
│ Schema (JSON, UTF-8)                │
├─────────────────────────────────────┤
│ Block Table (JSON, UTF-8)           │
├─────────────────────────────────────┤
│ Data Block 0 (JSON, UTF-8)          │
├─────────────────────────────────────┤
│ Data Block 1 (JSON, UTF-8)          │
├─────────────────────────────────────┤
│ ...                                 │
├─────────────────────────────────────┤
│ Data Block N (JSON, UTF-8)          │
├─────────────────────────────────────┤
│ Checksum (32 bytes, SHA-256)        │
└─────────────────────────────────────┘
```

## Header

| Field | Size | Type | Description |
|-------|------|------|-------------|
| magic | 4 bytes | bytes | Always `STG1` (0x53544731) |
| version | 1 byte | uint8 | Format version (currently 1) |
| flags | 1 byte | uint8 | Reserved flags, must be 0 |
| rotation_state | 4 bytes | uint32be | Logical rotation index |
| schema_len | 4 bytes | uint32be | Length of the schema JSON |

Total header size: 14 bytes. Packed as `!4sBBII`.

## Schema

A JSON object:

```json
{
  "fields": {
    "id": "integer",
    "name": "string",
    "meta.value": "float"
  }
}
```

Supported types:

- `string`
- `integer`
- `float`
- `boolean`
- `null`
- `array`
- `object`

Nested objects are flattened with dot notation.

## Block Table

A JSON array of `[offset, size]` pairs describing each data block. Offsets are absolute from the start of the serialized payload (header + schema + table + blocks).

```json
[[14, 120], [134, 120], [254, 120]]
```

## Data Blocks

Each block is a JSON array of records. Records are distributed round-robin by record index to keep the layout stable.

## Checksum

A 32-byte SHA-256 digest computed over the entire payload (everything before the checksum).

## Determinism

- JSON keys are sorted alphabetically.
- Whitespace is minimized.
- Records preserve input order during merge.
- UTF-8 is the only text encoding.

## Future Extensibility

- The `flags` byte is reserved.
- The `version` field allows format evolution.
- New dumper plugins can be added without changing the format.

## Security Notes

STANG is designed for data storage and interchange. It does not obfuscate data, bypass scanners, or hide malware. The format is transparent and documented.

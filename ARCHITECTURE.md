# STANG Architecture

This document explains the internal architecture of STANG from a developer perspective.

## Component Overview

```text
CLI
 │
 ▼
Encoder / Decoder / Dumper / Inspector / Verifier
 │
 ▼
STGContainer
 │
 ├── Header
 ├── Schema
 ├── Block Table
 ├── Data Blocks
 └── Checksum
 │
 ▼
RotationEngine
 │
 ▼
JSON / CSV / Raw Output
```

## Modules

### `stang.rotation`

Implements circular logical rotation. Never moves physical data. Exposes `rotate`, `current_index`, `current_position`, `normalize`, and `reset`.

### `stang.schema`

Infers and stores a flattened schema from JSON-compatible records. Supports nested objects via dot notation.

### `stang.blocks`

Round-robin partitioning and merging of records across blocks.

### `stang.checksum`

SHA-256 integrity checking with optional HMAC support. Uses constant-time comparison.

### `stang.container`

`STGContainer` is the in-memory representation. Handles serialization, deserialization, and validation.

### `stang.encoder`

Converts structured records into a `STGContainer` and writes `.stg` files.

### `stang.decoder`

Reads `.stg` files, validates them, and reconstructs the original records while respecting rotation state.

### `stang.dumpers`

Pluggable output formatters:

- `BlockDumper` — human-readable block view
- `JSONDumper` — pretty JSON
- `CSVDumper` — CSV export
- `RawDumper` — internal structure for debugging

### `stang.cli`

Argument parsing and command dispatch for the `stang` console script.

## Data Flow

### Encoding

```text
JSON records
    ↓
Schema.infer()
    ↓
blocks.partition_records()
    ↓
STGContainer(schema, blocks, rotation_state)
    ↓
serialize_payload() + checksum
    ↓
.stg file
```

### Decoding

```text
.stg file
    ↓
STGContainer.deserialize()
    ↓
checksum validation
    ↓
decode_stg()
    ↓
blocks.merge_blocks()
    ↓
JSON records
```

## Rotation Model

The rotation engine is initialized with the set of available block indices. Calling `rotate(n)` updates only a logical index:

```python
state = (state + n) % count
```

This means concurrent decoders can safely create their own rotation context without mutating shared state.

## Error Handling

All core modules raise domain-specific exceptions:

- `RotationError` (via `ValueError`/`TypeError`)
- `SchemaError`
- `ContainerError`
- Standard `ValueError` for bad parameters

The CLI catches these and prints friendly messages.

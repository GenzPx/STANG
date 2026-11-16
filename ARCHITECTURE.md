# STANG Architecture

This document explains the internal architecture of STANG from a developer perspective.

## Component Overview

```text
CLI / STANG Studio (web)
 │
 ▼
Encoder / Decoder / Dumper / Inspector / Verifier
 │
 ▼
STGContainer
 │
 ├── Header (magic, version, flags, rotation_state, …)
 ├── Header Extension (schema + KDF params)      [STG2]
 ├── Data Blocks (round-robin by record index)
 └── Trailer (SHA-256 | HMAC-SHA256 | AEAD MAC)
 │
 ▼
RotationEngine
 │
 ▼
JSON / CSV / TSV / NDJSON / Markdown / Raw Output
```

## Modules

### `stang.rotation`

Circular logical rotation. Never moves physical data. Exposes `rotate`, `rotate_to`,
`current_index`, `current_position`, `rotated_positions`, `normalize`, `reset`, `count`.

### `stang.schema`

Dot-flattened schema inferred across **all** records (`Schema.infer_many`), with numeric
widening (`integer + float → float`) and conflict widening to `any`. Nested objects collapse
into dotted paths. `validate_record` enforces a stored schema.

### `stang.blocks`

Round-robin partitioning (`partition_records`), canonical merge (`merge_blocks`) and the
rotated logical view (`rotate_blocks`).

### `stang.checksum`

Digest helpers: plain SHA-256 or HMAC-SHA256 (`compute_checksum`), constant-time comparison
(`verify_checksum`), payload digest (`container_checksum`).

### `stang.crypto`

Standard-library AEAD construction used by STG2:

- `derive_keys(passphrase, salt)` → `(enc_master, mac_key)` via PBKDF2-HMAC-SHA256 (100k).
- `encrypt_block` / `decrypt_block` — HMAC-SHA256 counter-mode stream cipher with a
  per-block domain-separated key (`"stang-blk" ‖ u32be(index) ‖ nonce`) and a 16-byte nonce.
- Nonces come from `secrets`; salt is random per container.

### `stang.container`

`STGContainer` — the in-memory representation. Auto-detects and reads **STG1** and **STG2**;
serializes to either (`format_version=1|2`). Enforces bounds checks, verifies the trailer
before parsing, and never returns partial data on failure. Secrets passed at
construction/deserialization are kept only to make re-serialization seamless and are excluded
from `repr()`.

### `stang.encoder`

`encode_stg` / `save_stg` / `encode_from_json` — records → `STGContainer`. Handles flags
(`compress`, `passphrase`, `integrity_key`), `format_version`, schema validation and
record-type checks.

### `stang.decoder`

`decode_stg` (canonical merge), `load_stg` (file + credentials), `decode_to_json`.

### `stang.errors`

`STANGError` → `ContainerError` → `ChecksumError` / `AuthenticationError` / `IntegrityError` /
`EncryptionError`, plus `SchemaError` from `stang.schema`. CLI maps these to friendly messages
and exit codes (0 ok · 1 error · 2 credentials required for `verify`).

### `stang.dumpers`

Pluggable output formatters: `block` (human overview), `json`, `ndjson`, `csv`, `tsv`,
`markdown` (`md`), `stats` (block distribution), `raw` (internal structure). Register new ones
in `DUMPERS`.

### `stang.nodes`

Base `Node` (request/response hooks, timeout) plus `Pipeline` for ordered request execution and
reverse-order response execution with `PipelineError` stage attribution.

### `stang.cli`

Subcommands: `init`, `encode`, `decode`, `dump`, `inspect`, `rotate`, `verify`, `convert`,
`keygen`, `status`. Secrets via env/file/prompt only; `-` means stdin/stdout.

## Data Flow

### Encoding (STG2, encrypted)

```text
JSON records
    ↓ Schema.infer_many()
blocks.partition_records()  (round-robin)
    ↓
canonical JSON per block
    ↓ (if compress) zlib level 9
    ↓ (if encrypt)  random nonce + HMAC-SHA256 counter-mode stream
header ‖ extension(schema[,kdf]) ‖ block entries
    ↓
HMAC-SHA256(mac_key, payload)  ← trailer
    ↓
.stg file
```

### Decoding

```text
.stg file
    ↓ sniff magic → STG1 | STG2
header validation (magic, version, flags, bounds)
    ↓
trailer verification (SHA-256 | HMAC | AEAD MAC)   ← before any parsing
    ↓
per block: decrypt → decompress → canonical JSON parse
    ↓
blocks.merge_blocks()  (canonical storage order)
    ↓
JSON records
```

## Rotation Model

```python
state = (state + offset) % count
```

Rotation changes only the logical index. Concurrent decoders hold independent
`RotationEngine` instances; the stored `rotation_state` is preserved through round-trips and
rewrites.

## Error Handling

- `stang.errors.*` — domain exceptions; CLI renders `error: …` and exits 1.
- `stang.schema.SchemaError` — schema inference/validation failures.
- `ValueError`/`TypeError` — API misuse.
- Dumpers raise `NotImplementedError` if a subclass forgets `dump`.

## Cross-Implementation Conformance

`tests/fixtures/golden*.stg` pin the wire format byte-for-byte (plain STG2, encrypted STG2
with pinned salt/nonces). The Python suite (`tests/test_vectors.py`) and the TypeScript
suite (`scripts/conformance.mjs`, using the same fixtures) both verify them, guaranteeing
the studio and the CLI produce identical bytes.

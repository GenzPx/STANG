# API Documentation

STANG exposes a Python API and a CLI. This page documents the Python API (v2.1.0).

## `stang.encode_stg`

```python
encode_stg(
    records,
    block_count=4,
    rotation_state=0,
    flags=0,
    *,
    passphrase=None,
    integrity_key=None,
    compress=False,
    format_version=2,
    validate=False,
) -> STGContainer
```

Encode records into a container.

- `passphrase` — encrypt block payloads (implies the AEAD scheme; mutually exclusive with `integrity_key`).
- `integrity_key` — require HMAC-SHA256 authenticity on the trailer.
- `compress` — zlib-compress block payloads before (optional) encryption.
- `format_version` — `2` (default) or `1` (legacy STG1; incompatible with compression/crypto).
- `validate` — validate every record against the inferred schema.

## `stang.save_stg`

```python
save_stg(path, records, block_count=4, rotation_state=0, flags=0, *, passphrase=None,
         integrity_key=None, compress=False, format_version=2, validate=False) -> None
```

Encode records and write a `.stg` file.

## `stang.encode_from_json`

```python
encode_from_json(data, block_count=4, *, passphrase=None, integrity_key=None,
                 compress=False, format_version=2, input_format="json") -> STGContainer
```

Accepts a single JSON object (one record) or an array of objects. With
`input_format="ndjson"`, expects newline-delimited JSON objects (blank lines and `#` comment
lines are ignored).

## `stang.decode_stg`

```python
decode_stg(container) -> list[dict]
```

Decode a container back to its original records, in canonical storage order.

## `stang.load_stg`

```python
load_stg(path, *, passphrase=None, integrity_key=None) -> list[dict]
```

Load and decode a `.stg` file (STG1 or STG2, auto-detected).

## `stang.decode_to_json`

```python
decode_to_json(container) -> bytes
```

Decode to a deterministic JSON byte payload (sorted keys, compact separators).

## `STGContainer`

```python
STGContainer(schema, blocks, rotation_state=0, flags=0, *,
             passphrase=None, integrity_key=None, format_version=2)
```

In-memory container. Useful members:

- `serialize(passphrase=None, integrity_key=None, *, salt=None, block_nonces=None) -> bytes`
- `serialize_payload(...) -> bytes` — everything except the trailer
- `STGContainer.deserialize(data, *, passphrase=None, integrity_key=None)` — auto-detects format
- Properties: `format_version`, `version`, `magic`, `is_compressed`, `is_encrypted`,
  `record_count`, `requires_passphrase`
- `describe() -> dict` — machine-readable summary (used by `inspect --json`)
- `rotated_records_order()` — `(block_index, intra_index)` pairs in logical read order

`salt` / `block_nonces` are advanced hooks for reproducible serialization (used by the
golden test vectors). Secrets passed to the container are never serialized and are excluded
from `repr()`.

## `Schema`

```python
Schema(fields=None)                    # explicit dot-flattened map
Schema.infer(record)                   # from one record
Schema.infer_many(records)             # merged across all records (widening rules)
schema.merge(other)                    # combine two schemas
schema.validate_record(record, allow_extra=True)
utils: to_dict / from_dict
```

Types: `string · integer · float · boolean · null · array · object · any`.

## `RotationEngine`

```python
RotationEngine(positions, initial_position=0)

engine.rotate(offset)          # relative turn, returns new index
engine.rotate_to(index)        # absolute set (normalized)
engine.current_index()
engine.current_position()
engine.rotated_positions()     # positions starting from active state
engine.normalize(offset)       # state-preserving normalization
engine.reset()
engine.count
```

## `Pipeline` / `Node` (extended routers)

```python
from stang.nodes import Node, Pipeline

class UppercaseNode(Node):
    def process_request(self, request):
        request["name"] = str(request["name"]).upper()
        return request

pipeline = Pipeline([UppercaseNode()])
pipeline.process_request({"name": "genz"})    # {"name": "GENZ"}
pipeline.process_response({"ok": True})       # reverse order
```

`PipelineError` carries `.node` and `.stage` (`"request"` | `"response"`).

## Exceptions

All under `stang.errors` (re-exported at package top level for the common ones):

- `STANGError` — base class
- `ContainerError(STANGError, ValueError)` — malformed/corrupt/invalid container
- `ChecksumError(ContainerError)` — plain digest mismatch
- `AuthenticationError(ContainerError)` — AEAD trailer verification failed (wrong passphrase or tampering)
- `IntegrityError(ContainerError)` — HMAC key wrong/missing
- `EncryptionError(ContainerError)` — crypto parameters missing/invalid
- `SchemaError(ValueError)` — schema inference/validation failure

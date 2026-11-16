# Testing

## Running Tests

```bash
pytest                      # or: pytest -v
pytest --cov=stang
```

## Test Categories

### Unit Tests

`test_rotation.py`, `test_schema`-adjacent tests in `test_encoding.py`, and `test_crypto.py`
(key-derivation vectors, keystream pinning, nonce behavior).

### Golden Vectors

`test_vectors.py` validates `tests/fixtures/golden*.stg` byte-for-byte. The same fixtures are
consumed by the TypeScript implementation via `scripts/conformance.mjs` — run it with
`node scripts/conformance.mjs` (or `npm run conformance`).

### CLI End-to-End

`test_cli.py` drives `stang.cli.main()` with temporary files: encode/decode/verify/rotate/
convert/dump/inspect/keygen, credential handling and exit codes.

### Integrity & Security

`test_integrity.py` — corrupted digests, wrong passphrases, wrong HMAC keys, header tampering,
truncated files, v1 checksum enforcement.

### Dumpers & Nodes

`test_dumpers.py` — every registered dumper on sample and empty containers.
`test_nodes.py` — pipeline ordering (request forward, response reverse), timeout wrapping,
`PipelineError` attribution.

### Cross-check

`verify.py` performs a fast standalone sanity check; it is not a substitute for pytest.

### Concurrency

Ensure each request uses its own `RotationEngine` context; the library keeps no global state.

## Frontend

```bash
npm install
npm run typecheck
npm run build
npm run conformance
```

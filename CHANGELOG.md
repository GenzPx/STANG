# Changelog

All notable changes to STANG are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-11-16

Hardening and interoperability release. Format unchanged (STG2 stays STG2); writers and
readers are stricter and byte-agreement between the Python and TypeScript implementations
is now enforced by CI-grade checks.

### Added

- `stang diff A.stg B.stg [--json]` — semantic, order-independent record comparison of two
  containers (multiset on canonical JSON fingerprints). Exit `0` identical · `1` different ·
  `2` credentials required. Header/format/flags/rotation differences are reported as
  informational notes and never affect the exit code.
- `stang encode --input-format ndjson` — newline-delimited JSON input (blank lines and `#`
  comment lines are ignored).
- Canonical JSON suite in `scripts/conformance.mjs` (float rendering, astral-plane key
  ordering) and at Python level (`tests/test_canonical_json.py`).

### Fixed

- **Cross-implementation canonical JSON**: the TypeScript codec now renders numbers exactly
  like Python's `json.dumps(..., ensure_ascii=False)` — integer literals below 1e16,
  scientific notation with two-digit signed exponents at ≥ 1e16 / < 1e-4, and code-point
  key ordering (was UTF-16). Verified on 500 random doubles against the Python reference.
- Integrity/consistency: containers with `FLAG_ENCRYPTED | FLAG_HMAC` are rejected at
  construction time, not only at serialize time.

### Security

- **Strict flag validation**: readers reject unknown flag bits (STG2) and any non-zero flags
  (STG1) instead of silently masking them.
- **Strict JSON everywhere**: NaN/Infinity no longer parse inside STG containers or as
  encoder input; `json.dumps(..., allow_nan=False)` on the Python writer path.

## [2.0.0] - 2026-11-16

A ground-up upgrade: new wire format, encryption, compression, a second (TypeScript)
implementation, and a byte-conformance test harness between them. Fully backward compatible
with STG1 containers.

### Added

- **STG2 wire format** — 32-byte header, JSON header extension (schema + KDF parameters),
  length-prefixed block entries, flags bitfield (`0x01` compressed, `0x02` encrypted,
  `0x04` HMAC), 4 MiB extension cap. See `SPEC.md`.
- **Encryption** — per-block PBKDF2-HMAC-SHA256 (100k iterations) keyed stream cipher
  (HMAC-SHA256 counter mode), 16-byte random nonce per block, Encrypt-then-MAC trailer.
  Cross-implemented and verified in Python and TypeScript.
- **HMAC-SHA256 integrity mode** — `--hmac` authenticates containers without hiding data.
- **zlib compression** — `compress=True` / `--compress`, per block, level 9.
- **Schema inference across all records** (`Schema.infer_many`) with numeric widening and
  `any` widening; record validation API (`validate_record`).
- **New dumpers** — NDJSON, TSV, Markdown table (`markdown`/`md`), and `stats` (block
  distribution). All registered in `DUMPERS`.
- **`Pipeline` / `PipelineError`** — real ordered request/reverse-response execution with
  timeout enforcement and stage-attributed errors (`stang.nodes`).
- **CLI**: `keygen`, `convert` (STG1↔STG2), `--pretty` decode output, `--json` inspect
  output, `--format stg1|stg2` on encode/init, `--compress`, `--encrypt`, `--hmac`,
  `--passphrase-env/--passphrase-file`, `--key-env/--key-file`, stdin/stdout via `-`,
  exit code 2 for "credentials required", secrets never accepted as bare arguments.
- **STANG Studio** — React/TypeScript interactive workbench (`src/`): byte-map
  visualization, hex dump with segment highlighting, rotation dial, block inspector,
  `.stg` import/export, full STG1/STG2 codec (`src/stg/codec.ts`).
- **Golden test vectors** (`tests/fixtures/`) and `scripts/conformance.mjs` verifying
  byte-equality between the Python and TypeScript implementations.
- **Test suite** grew from 24 to 97 tests: crypto vectors, CLI end-to-end, dumpers,
  nodes, schema, integrity and cross-language fixtures.
- `stang.errors` module with a proper exception hierarchy
  (`STANGError` → `ContainerError` → `AuthenticationError`/`IntegrityError`/`EncryptionError`/`ChecksumError`).
- GitHub Actions workflow for the web studio (typecheck + build + conformance).

### Changed

- **Default wire format is now STG2** (`format_version=2`). STG1 remains readable and
  writable (`--format stg1`, `format_version=1`) and is detected automatically on read.
- `encode_stg` / `save_stg` accept `passphrase=`, `integrity_key=`, `compress=`,
  `format_version=`, `validate=`.
- `STGContainer.deserialize()` auto-detects STG1/STG2 and takes `passphrase=` /
  `integrity_key=` keyword arguments.
- `inspect` on an encrypted container without credentials shows header metadata only;
  `verify` exits with code 2 in that situation instead of failing.
- `rotate` transparently re-encrypts encrypted containers (fresh nonces, same salt).
- `pyproject.toml`: ruff per-file ignores for tests, lint section layout, package renamed
  metadata bump; `.gitignore` now covers Node/Vite artifacts.
- Ruff configuration moved to `[tool.ruff.lint]` (top-level options deprecated).

### Fixed

- Ruff violations across the package (docstrings, imports, line lengths) and mypy strict
  errors (`dumpers/csv.py`, `cli.py` return type).
- `verify.py` rotation overflow expectation (0 → 4) for sequential rotations.
- `rotation_state` is normalized modulo block count on construction.
- Schema inference no longer silently overwrites field types from the last record;
  fields widen across records.
- `markdown` dumper renders booleans as `true`/`false`.

### Security

- Verification happens before any payload parsing, in both implementations.
- Encrypted containers fail at the trailer check on wrong passphrases without examining blocks.
- Secrets are excluded from `repr()` and never written to disk by the tools.
- See `SECURITY.md` and `SPEC.md` for the threat model and exact constructions.

## [1.0.0] - Initial release

- Initial STANG file format (version 1).
- `STGContainer` with header, schema, block table, data blocks, and SHA-256 checksum.
- `RotationEngine` implementing circular logical rotation.
- Encoder (`stang encode`) and decoder (`stang decode`).
- Dumper plugin system with `block`, `json`, `csv`, and `raw` formats.
- CLI commands: `init`, `encode`, `decode`, `dump`, `inspect`, `rotate`, `verify`.
- Documentation: README, SPEC, ARCHITECTURE, CONTRIBUTING, and full `docs/` directory.

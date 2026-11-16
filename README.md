# STANG

> **STANG is a rotational data container. It doesn't walk through data. It turns.**

STANG is a custom, versioned, self-describing file format and toolkit for storing structured data in `.stg` files — with a built-in rotational access model, authenticated integrity and optional encryption. It is **not** a database engine, **not** an SQL database, and **not** a replacement for SQLite or PostgreSQL. STANG is a container that accesses records through a circular rotation model rather than linear cursors.

---

## Highlights

- **Rotational access** — records are packed round-robin into blocks; a `rotation_state` integer in the header decides where logical reading starts. Rotating a container rewrites 4 bytes, never the payload.
- **Byte-deterministic** — canonical JSON with sorted keys, stable layouts, reproducible output across runs (and across the Python and TypeScript implementations).
- **Sealed containers** — every file ends with a 32-byte digest covering all preceding bytes: SHA-256, keyed HMAC-SHA256, or an Encrypt-then-MAC AEAD for encrypted files.
- **Compression** — per-block zlib (RFC 1950), typically 50–60% smaller on text records.
- **Encryption** — PBKDF2-HMAC-SHA256 (100k iterations) → per-block HMAC-SHA256 counter-mode stream, per-block nonce, Encrypt-then-MAC trailer.
- **Self-describing** — dot-flattened schema inferred across *all* records and embedded in the header extension.
- **Two wire formats** — STG2 (current) and STG1 (legacy, read/write for compatibility).
- **Zero runtime dependencies** — Python ≥ 3.10 stdlib only.
- **STANG Studio** — an interactive browser workbench (encode/decode/inspect/verify) shipped in this repository, byte-compatible with the Python package.

---

## Installation

Requires **Python 3.10+**.

```bash
git clone https://github.com/GenzPx/STANG.git
cd STANG
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Verify:

```bash
stang --version   # stang 2.0.0
stang status
```

---

## Quick Start

```bash
cat > people.json <<'EOF'
[
  {"id": 1, "name": "Genz", "value": "example", "active": true},
  {"id": 2, "name": "Ana", "value": "sample", "active": false}
]
EOF

stang encode people.json people.stg --blocks 4 --rotation 1 --compress
stang inspect people.stg
stang verify people.stg
stang dump people.stg --format markdown
stang decode people.stg people-out.json
```

Encrypt with a passphrase:

```bash
export STANG_PASSPHRASE="$(stang keygen)"
stang encode people.json people.stg --encrypt --passphrase-env STANG_PASSPHRASE
stang decode people.stg out.json --passphrase-env STANG_PASSPHRASE
```

Decode semantics guarantee `decode(encode(data)) == data` regardless of rotation state.

---

## STANG Studio (browser)

An interactive single-page workbench lives in this repository: pick a sample dataset or paste JSON, encode it with your chosen block count / rotation / flags, and watch the container come apart byte-by-byte — segment map, hex dump, block inspector, schema table, integrity badge. It decodes pasted hex/base64 or dropped `.stg` files, and the codec is **byte-compatible with the Python package** (see `scripts/conformance.mjs`).

```bash
npm install
npm run build       # produces dist/index.html (single file)
npm run dev         # local dev server
npm run conformance # verify JS codec == Python codec on golden vectors
```

Open the built page, or run `npm run preview`.

---

## CLI at a glance

| Command | Purpose |
|---------|---------|
| `stang init FILE [--blocks N] [--compress] [--encrypt] [--hmac]` | Create an empty container |
| `stang encode INPUT.json OUTPUT.stg [--blocks N] [--rotation N] [--compress] [--encrypt] [--hmac] [--format stg1\|stg2]` | Encode JSON → `.stg` |
| `stang decode INPUT.stg OUTPUT.json [--pretty]` | Decode `.stg` → JSON |
| `stang dump INPUT.stg [--format block\|json\|ndjson\|csv\|tsv\|markdown\|stats\|raw]` | Render records with a dumper plugin |
| `stang inspect INPUT.stg [--json]` | Header metadata without full decode |
| `stang rotate INPUT.stg OFFSET` | Bump the logical rotation state (±N) |
| `stang verify INPUT.stg` | Authenticate; exit 0 valid · 1 invalid · 2 credentials required |
| `stang convert INPUT.stg OUTPUT.stg --to stg1\|stg2` | Re-wrap between wire formats |
| `stang keygen [--bytes N] [--hex]` | Generate a strong random passphrase |
| `stang status` | Runtime summary |

Secrets are never passed as bare arguments — use `--passphrase-env VAR`, `--passphrase-file PATH`, `--key-env VAR` or `--key-file PATH`, or the interactive prompt. `-` as file argument means stdin/stdout.

Full reference: [`docs/cli.md`](docs/cli.md).

---

## API overview

```python
from stang import encode_stg, decode_stg, save_stg, load_stg

records = [{"id": 1, "name": "Genz"}]
container = encode_stg(records, block_count=4, rotation_state=1, compress=True)
assert decode_stg(container) == records

save_stg("data.stg", records, compress=True)
assert load_stg("data.stg") == records

# Encryption
save_stg("secret.stg", records, passphrase="correct horse battery staple")
assert load_stg("secret.stg", passphrase="correct horse battery staple") == records
```

Full reference: [`docs/api.md`](docs/api.md).

---

## How a container fits together (STG2)

```text
┌──────────────┬───────────────────┬───────────────────────┬──────────┐
│ Header · 32B │ Extension · JSON  │ Block entries · len+  │ Trailer  │
│ magic STG2   │ schema + (kdf)    │ blob (zlib/AEAD)      │ 32 B     │
│ flags rotation ext_len …          │                       │ SHA-256/ │
│ salt         │                   │                       │ HMAC     │
└──────────────┴───────────────────┴───────────────────────┴──────────┘
```

Normative details: [`SPEC.md`](SPEC.md).

## Core concepts

| Concept | Description |
|---------|-------------|
| Container | One `.stg` file: header, extension, blocks, trailer |
| Block | A subset of records; round-robin by record index |
| Schema | Dot-flattened field types, merged across all records |
| Rotation state | Logical read offset; `(state + offset) mod N` |
| Trailer | 32-byte digest over everything before it |

---

## Project structure

```text
stang/            # Python package (zero runtime deps)
  container.py    #   STG1 + STG2 serialization & validation
  crypto.py       #   PBKDF2 + HMAC-SHA256 AEAD construction
  encoder.py decoder.py blocks.py rotation.py schema.py checksum.py errors.py
  cli.py nodes.py dumpers/
src/              # STANG Studio (React + TypeScript, single-file build)
  stg/codec.ts    #   byte-compatible TS implementation of the format
  components/     #   encode/decode panels, byte map, rotation dial, hex view
tests/            # pytest suite (97 tests) + golden cross-language vectors
scripts/          # conformance.mjs — Python ↔ JS byte-equality checks
examples/ docs/ SPEC.md ARCHITECTURE.md
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                      # 97 tests
ruff check stang tests      # lint
mypy stang                  # strict type-check
npm install && npm run build && npm run conformance
```

CI runs ruff + mypy + pytest on Python 3.10–3.12 and builds the studio on Node 22.

---

## Security

- SHA-256 detects accidental corruption; HMAC-SHA256 and AEAD detect tampering.
- Verification always happens **before** payload parsing; a bad file never yields partial records.
- STANG is a container, not a security boundary: header, salt, extension (schema field names) and block nonces are visible. Use opaque field names if that matters.
- Never ship passphrases on the command line; use env vars or files.

See [`SECURITY.md`](SECURITY.md) and [`docs/security.md`](docs/security.md).

---

## Roadmap

- [x] Optional encryption layer (AEAD, Encrypt-then-MAC)
- [x] HMAC-SHA256 authenticated containers
- [x] Compression support (zlib, per block)
- [x] Additional dumper plugins (NDJSON, TSV, Markdown, stats)
- [x] Byte-compatible web implementation + conformance vectors
- [ ] Streaming encoder for very large files
- [ ] Language bindings reference (Go / Rust)

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `Checksum mismatch` | File corrupted | Restore from backup |
| `Authentication failed` | Wrong passphrase or tampered file | Check credentials; re-verify source |
| `Integrity check failed` | Wrong/missing HMAC key | Supply `--key-env`/`--key-file` |
| `Invalid magic bytes` | Not a `.stg` file | Check input file |
| `Unsupported STG version` | Tool too old/new | Upgrade STANG |
| `File too short` | Truncated file | Re-encode from source |

See [`docs/troubleshooting.md`](docs/troubleshooting.md) for more.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

See [`LICENSE`](LICENSE) — LICENSE TO BE DETERMINED (all rights reserved).

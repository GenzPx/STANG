# STANG

> **STANG is a rotational data container. It doesn't walk through data. It turns.**

STANG is a custom, versioned, self-describing file format and toolkit for storing structured data in `.stg` files. It is **not** a database engine, **not** an SQL database, and **not** a replacement for SQLite or PostgreSQL. STANG is an experimental data container that accesses records through a circular rotation model rather than linear cursors.

---

## Table of Contents

1. [Quick Description](#quick-description)
2. [Architecture Diagram](#architecture-diagram)
3. [How STANG Works](#how-stang-works)
4. [Why STANG Exists](#why-stang-exists)
5. [Core Concepts](#core-concepts)
6. [Routing Concept](#routing-concept)
7. [Rotation Concept](#rotation-concept)
8. [Supported Backends](#supported-backends)
9. [Installation](#installation)
10. [Quick Start](#quick-start)
11. [Configuration Example](#configuration-example)
12. [CLI Examples](#cli-examples)
13. [API Overview](#api-overview)
14. [Project Structure](#project-structure)
15. [Development](#development)
16. [Testing](#testing)
17. [Security](#security)
18. [Troubleshooting](#troubleshooting)
19. [Roadmap](#roadmap)
20. [Contributing](#contributing)
21. [License](#license)

---

## Quick Description

STANG stores structured records inside a `.stg` file. Internally, records are split into blocks. Instead of a cursor that moves forward or backward, STANG exposes a **rotation engine**:

- `rotate(+n)` — turn forward
- `rotate(-n)` — turn backward
- `current()` — inspect the active block
- `read()` — decode records from the rotated view

Rotations are purely logical. The physical block order never changes; only the logical offset does.

---

## Architecture Diagram

```text
                 ┌─────────────┐
                 │   DUMPER    │
                 └──────┬──────┘
                        │
                        ▼
                 ┌─────────────┐
                 │     CLI     │
                 └──────┬──────┘
                        │
                        ▼
              ┌───────────────────┐
              │       STANG       │
              │  Rotational Data  │
              │     Container     │
              └─────────┬─────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │ Encoder │   │ Rotation │   │ Decoder  │
    └────┬────┘   │  Engine  │   └────┬─────┘
         │        └──────────┘        │
         ▼                            ▼
    ┌─────────┐                  ┌──────────┐
    │  .stg   │                  │   JSON   │
    │  file   │                  │  /CSV    │
    └─────────┘                  └──────────┘
```

> This diagram is an illustrative example. STANG is a file-format toolkit; the actual pipeline is configured by the commands you run.

---

## How STANG Works

1. **Input** — JSON records are read from a file or API.
2. **Schema inference** — STANG infers a flat schema from the records.
3. **Block partitioning** — Records are distributed round-robin across N blocks.
4. **Rotation state** — A logical rotation index is stored in the header.
5. **Serialization** — Header, schema, block table, blocks, and checksum are written.
6. **Decode** — The file is validated, blocks are reordered from the rotation state, and records are merged.

---

## Why STANG Exists

STANG was created as an educational and experimental format to explore:

- Non-linear data access models.
- Self-describing, versioned binary containers.
- Deterministic encode/decode round-trips.
- Pluggable output dumpers.

It is intentionally simple and uses only the Python standard library at runtime.

---

## Core Concepts

| Concept | Description |
|--------|-------------|
| Container | A single `.stg` file holding metadata, schema, blocks, and checksum. |
| Block | A subset of records stored inside the container. |
| Schema | Flattened type description of record fields. |
| Rotation state | Logical index indicating the current active block. |
| Checksum | SHA-256 integrity digest over the payload. |

---

## Routing Concept

In STANG, "routing" refers to how a request or decode operation flows through the container:

```text
Request
   ↓
STANG Container
   ↓
RotationEngine (select current view)
   ↓
Block reordering
   ↓
Record merge
   ↓
Output (JSON/CSV/Raw)
```

This is a conceptual model. The CLI implements it through `encode`, `decode`, `rotate`, and `dump`.

---

## Rotation Concept

Imagine a steering wheel with four positions:

```text
A → B → C → D → A
A ← D ← C ← B ← A
```

With four nodes and current state `3`:

```text
rotate(+1) → (3 + 1) % 4 = 0
```

STANG never moves data when rotating. It only changes the logical offset used during decode.

---

## Supported Backends

STANG does not require an external database. The default storage backend is the local filesystem via `.stg` files. The example documentation uses SQLite as a conceptual backend adapter, but the core format is backend-agnostic.

---

## Installation

Requires Python 3.10 or newer.

```bash
git clone <repository>
cd stang
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

Verify:

```bash
stang --version
stang --help
```

---

## Quick Start

Create a JSON file:

```bash
cat > people.json <<'EOF'
[
  {"id": 1, "name": "Genz", "value": "example"},
  {"id": 2, "name": "Ana", "value": "sample"}
]
EOF
```

Encode, inspect, dump, and decode:

```bash
stang encode people.json people.stg --blocks 4 --rotation 1
stang inspect people.stg
stang dump people.stg
stang dump people.stg --format json
stang decode people.stg people-out.json
```

---

## Configuration Example

A conceptual YAML configuration for an extended STANG router (not required for the CLI):

```yaml
stang:
  name: demo-router

rotation:
  mode: circular
  initial_position: 0

nodes:
  - id: A
    type: validation
  - id: B
    type: transform
  - id: C
    type: backend
```

See `docs/configuration.md` for full details.

---

## CLI Examples

```bash
stang init empty.stg
stang encode input.json output.stg --blocks 8 --rotation 3
stang decode output.stg input.json
stang dump output.stg
stang dump output.stg --format csv
stang dump output.stg --format raw
stang inspect output.stg
stang rotate output.stg +1
stang verify output.stg
```

---

## API Overview

```python
from stang import encode_stg, decode_stg, save_stg, load_stg

records = [{"id": 1, "name": "Genz"}]
container = encode_stg(records, block_count=4, rotation_state=1)

assert decode_stg(container) == records

save_stg("data.stg", records)
assert load_stg("data.stg") == records
```

---

## Project Structure

```text
stang/
├── stang/
│   ├── __init__.py
│   ├── cli.py
│   ├── container.py
│   ├── encoder.py
│   ├── decoder.py
│   ├── rotation.py
│   ├── checksum.py
│   ├── schema.py
│   ├── blocks.py
│   └── dumpers/
│       ├── __init__.py
│       ├── json.py
│       ├── csv.py
│       ├── raw.py
│       └── block.py
├── tests/
├── docs/
├── examples/
├── README.md
├── SPEC.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── LICENSE
└── pyproject.toml
```

---

## Development

```bash
git clone <repository>
cd stang
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Testing

```bash
pytest
pytest -v
pytest --cov=stang
```

---

## Security

STANG uses checksums and magic/version validation to detect accidental corruption. It does not provide encryption or authentication by default. Never store secrets in `.stg` files unless you encrypt them first. See `SECURITY.md` and `docs/security.md`.

---

## Troubleshooting

| Problem | Cause | Solution |
|--------|-------|----------|
| `Checksum mismatch` | File corrupted | Restore from backup |
| `Invalid magic bytes` | Not a `.stg` file | Check input file |
| `Unsupported STG version` | Old/new tool | Upgrade/downgrade STANG |
| `File too short` | Truncated file | Re-encode from source |

See `docs/troubleshooting.md` for more.

---

## Roadmap

- [ ] Optional encryption layer
- [ ] Streaming encoder for large files
- [ ] Additional dumper plugins (YAML, TOML)
- [ ] Compression support
- [ ] Language bindings reference

---

## Contributing

We welcome contributions. Please read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` first.

```bash
git checkout -b feature/my-feature
pytest
git commit -m "feat: add ..."
git push origin feature/my-feature
```

---

## License

See `LICENSE`. Until a license is chosen explicitly, the placeholder text reads:

> LICENSE TO BE DETERMINED

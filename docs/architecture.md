# Architecture

## Component Diagram

```text
CLI
 │
 ▼
API (Python module)
 │
 ▼
STANG Container
 │
 ├── RotationEngine
 ├── Pipeline (stang.nodes)
 ├── Node system (stang.nodes)
 ├── Header Extension (schema + KDF)   [STG2]
 └── Trailer (SHA-256 | HMAC | AEAD)
```

## Responsibilities

### CLI

Parses user commands and dispatches to the appropriate module.

### API

Programmatic interface (`encode_stg`, `decode_stg`, `STGContainer`, etc.).

### STANG Container

Holds the parsed or created file representation: header, extension (schema), blocks, trailer. Auto-detects STG1/STG2.

### RotationEngine

Maintains circular logical state without mutating data.

### RouteResolver / Pipeline / Nodes

Conceptual components for routing requests through validation, transformation, and backend stages. Not required for the file-format CLI but documented for extensibility.

### Backend Adapter

Could connect STANG to SQLite or another store. The core format is filesystem-based.

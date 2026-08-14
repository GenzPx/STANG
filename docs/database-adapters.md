# Database Adapters

STANG is a file-format container, not a database. However, you can build adapters that bridge STANG to databases.

## Architecture

```text
STANG
   ↓
DatabaseAdapter
   ↓
SQLiteAdapter
   ↓
SQLite
```

## SQLite Adapter Example (Conceptual)

```python
class SQLiteAdapter:
    def __init__(self, path):
        self.path = path

    def load(self):
        # Read records from SQLite and encode to STG.
        pass

    def save(self, container):
        # Decode STG and write records to SQLite.
        pass
```

## Creating a New Adapter

1. Subclass `DatabaseAdapter`.
2. Implement `load` and `save`.
3. Register the adapter class.

## Why SQLite for MVP?

SQLite is lightweight, file-based, and requires no external server. It serves as a practical example backend.

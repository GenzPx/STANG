# Testing

## Running Tests

```bash
pytest
pytest -v
pytest --cov=stang
```

## Test Categories

### Unit Tests

Test individual modules such as `rotation.py`, `checksum.py`, and `schema.py`.

### Integration Tests

`test_encoding.py` and `test_decoding.py` verify JSON → STG → JSON round-trips.

### Routing Tests

Conceptual routing tests can be added when custom nodes are implemented.

### Rotation Tests

`test_rotation.py` covers positive, negative, overflow, and reset behavior.

### Adapter Tests

Add tests for any database adapter under `tests/test_adapters/`.

### API Tests

For HTTP wrappers, use `pytest` with `httpx` or `requests`.

### Concurrency Tests

Ensure each request uses its own `RotationEngine` context.

### Failure Tests

`test_integrity.py` covers checksum corruption, invalid magic, and truncated files.

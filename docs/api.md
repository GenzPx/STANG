# API Documentation

STANG exposes a Python API and a CLI. This page documents the Python API.

## `stang.encode_stg`

```python
encode_stg(records, block_count=4, rotation_state=0, flags=0) -> STGContainer
```

Encode records into a container.

## `stang.save_stg`

```python
save_stg(path, records, block_count=4, rotation_state=0, flags=0) -> None
```

Encode records and write a `.stg` file.

## `stang.decode_stg`

```python
decode_stg(container) -> list[dict]
```

Decode a container back to its original records.

## `stang.load_stg`

```python
load_stg(path) -> list[dict]
```

Load and decode a `.stg` file.

## `STGContainer`

In-memory container. Use `serialize()` and `deserialize()` for byte operations.

## `RotationEngine`

```python
RotationEngine(positions, initial_position=0)
```

Circular rotation engine.

Methods:

- `rotate(offset)`
- `current_index()`
- `current_position()`
- `normalize(offset)`
- `reset()`

## Exceptions

- `ContainerError`
- `SchemaError`

# Rotation

Rotation is the central concept of STANG.

## Mental Model

Think of a stang motor (handlebar) locked into positions. You do not push forward or backward linearly; you turn.

```text
A → B → C → D → A
A ← D ← C ← B ← A
```

## Modular Arithmetic

For a container with `N` blocks and current state `s`:

```text
new_state = (s + offset) mod N
```

Example with 4 blocks and current state 3:

```text
rotate(+1) → (3 + 1) % 4 = 0
```

## Logical vs Physical

STANG never moves block bytes when rotating. Only the logical offset changes. This makes rotation O(1).

## API

```python
from stang.rotation import RotationEngine

engine = RotationEngine([0, 1, 2, 3, 4])
engine.rotate(2)
engine.current_position()  # 2
engine.rotate(-1)
engine.current_position()  # 1
```

## CLI

```bash
stang rotate data.stg +2    # bump forward
stang rotate data.stg -1    # bump backward
```

On encrypted containers the file is transparently re-sealed with fresh nonces; the passphrase
is requested via `--passphrase-env` / `--passphrase-file`.

## Concurrency

Rotation state must live in a safe context (e.g., per-request). Do not share a single `RotationEngine` across concurrent requests unless it is read-only.

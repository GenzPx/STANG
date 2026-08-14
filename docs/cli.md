# CLI Documentation

The `stang` command provides all user-facing operations.

## Global Options

```bash
stang --version
stang --help
```

## Commands

### `stang init <file>`

Create an empty STG container.

```bash
stang init empty.stg
```

### `stang encode <input.json> <output.stg>`

Encode JSON to STG.

Options:

- `--blocks N` — number of blocks (default 4)
- `--rotation N` — initial rotation state

```bash
stang encode data.json data.stg --blocks 8 --rotation 3
```

### `stang decode <input.stg> <output.json>`

Decode STG to JSON. The output is always semantically identical to the
original input regardless of the stored rotation state.

```bash
stang decode data.stg output.json
```

### `stang dump <input.stg>`

Dump container contents.

- `--format {block,json,csv,raw}`

```bash
stang dump data.stg
stang dump data.stg --format json
```

### `stang inspect <input.stg>`

Show metadata without full decode.

### `stang rotate <input.stg> <offset>`

Update the container's rotation state.

```bash
stang rotate data.stg +1
stang rotate data.stg -2
```

### `stang verify <input.stg>`

Check file integrity.

```bash
stang verify data.stg
```

### `stang status`

Show runtime status.

```bash
stang status
```

## Conceptual Extended Commands

In extended STANG router deployments, the following commands may be implemented:

- `stang start`
- `stang stop`
- `stang routes`
- `stang logs`

They are not part of the core file-format CLI.

## Common Errors

- `Checksum mismatch` — file corrupted.
- `Invalid magic bytes` — wrong file type.
- `Unsupported STG version` — version mismatch.

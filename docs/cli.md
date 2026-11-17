# CLI Documentation

The `stang` command provides all user-facing operations. STG1 and STG2 files are auto-detected.

## Global Options

```bash
stang --version
stang --help
```

## Commands

### `stang init <file>`

Create an empty STG container.

```bash
stang init ledger.stg --blocks 8 --compress
stang init legacy.stg --format stg1
```

### `stang encode <input.json> <output.stg>`

Encode JSON to STG. `-` means stdin/stdout.

Options:

- `--blocks N` — number of blocks (default 4)
- `--rotation N` — initial rotation state
- `--compress` — zlib-compress block payloads
- `--encrypt` — AEAD-encrypt blocks (prompts for passphrase)
- `--hmac` — HMAC-SHA256 authenticity instead of plain SHA-256
- `--passphrase-env VAR` / `--passphrase-file PATH` — passphrase source
- `--key-env VAR` / `--key-file PATH` — raw integrity key source
- `--format stg1|stg2` — wire format (default stg2)
- `--input-format json|ndjson` — input syntax (default `json`; `ndjson` accepts newline-delimited objects, `#` comment lines and blank lines ignored)

```bash
stang encode data.json data.stg --blocks 8 --rotation 3 --compress
export STANG_PASSPHRASE="$(stang keygen)"
stang encode data.json data.stg --encrypt --passphrase-env STANG_PASSPHRASE
```

### `stang decode <input.stg> <output.json>`

Decode STG to JSON. The output is semantically identical to the original input regardless of
the stored rotation state.

- `--pretty` — indent the JSON output

```bash
stang decode data.stg out.json --pretty
stang decode data.stg - < data.stg          # to stdout
```

### `stang dump <input.stg>`

Dump container contents.

- `--format {block,json,ndjson,csv,tsv,markdown,md,stats,raw}`

```bash
stang dump data.stg                      # human block listing
stang dump data.stg --format ndjson
stang dump data.stg --format markdown    # GitHub-flavoured table
stang dump data.stg --format stats       # per-block distribution
```

### `stang inspect <input.stg>`

Show metadata without full decode.

- `--json` — machine-readable output

On an encrypted container without credentials, prints header metadata only and never the schema.

```bash
stang inspect data.stg
stang inspect data.stg --json | jq .rotation_state
```

### `stang rotate <input.stg> <offset>`

Update the container's rotation state (`+2`, `-1`, `5`). Rewrites only the rotation bytes;
encrypted files are re-sealed transparently (fresh nonces).

```bash
stang rotate data.stg +1
stang rotate data.stg -2
```

### `stang verify <input.stg>`

Check integrity/authenticity.

Exit codes: `0` valid · `1` invalid · `2` credentials required.

```bash
stang verify data.stg
stang verify secret.stg --passphrase-env STANG_PASSPHRASE
```

### `stang diff <a.stg> <b.stg>`

Semantic comparison of two containers — record order in blocks is ignored. Reports record
deltas (multiset, canonical JSON fingerprint), schema/format/flags/block/rotation differences.

Exit codes: `0` identical records · `1` different records · `2` credentials required.

- `--json` — machine-readable report

```bash
stang diff before.stg after.stg
stang diff a.stg b.stg --json | jq .identical_records
```

Note: rotation differences are reported as informational notes; they do not affect the exit code.

### `stang convert <input.stg> <output.stg> --to stg1|stg2`

Re-wrap between wire formats. Converting to STG1 refuses to silently drop compression or crypto.

```bash
stang convert legacy.stg current.stg --to stg2
```

### `stang keygen [--bytes N] [--hex]`

Generate a strong random passphrase (default 32 bytes, base64url).

```bash
stang keygen
```

### `stang status`

Show runtime status: version, platform, crypto suite, formats.

## Credentials

Secrets are never accepted as bare arguments. Priority: `--*-env` → `--*-file` → interactive
prompt (TTY only). For `verify` on encrypted/keyed files without any of these, the exit code is `2`.

| Flag | Meaning |
|------|---------|
| `--passphrase-env VAR` | Passphrase from environment variable |
| `--passphrase-file PATH` | Passphrase from file (trailing newline stripped) |
| `--key-env VAR` | Raw integrity key from environment variable |
| `--key-file PATH` | Raw integrity key bytes from file |

## Conceptual Extended Commands

In extended STANG router deployments, the following commands may be implemented:

- `stang start`
- `stang stop`
- `stang routes`
- `stang logs`

They are not part of the core file-format CLI.

## Common Errors

- `Checksum mismatch` — file corrupted (plain mode).
- `Authentication failed: wrong passphrase or corrupted data.` — AEAD verification failed.
- `Integrity check failed: bad key or corrupted data.` — HMAC verification failed.
- `Invalid magic bytes` — not an `.stg` file.
- `Unsupported STG version` — version mismatch.
- `File too short` — truncated file.

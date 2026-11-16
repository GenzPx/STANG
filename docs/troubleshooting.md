# Troubleshooting

## STANG fails to start

**Cause**: Python version is too old or the package is not installed.

**Solution**:

```bash
python --version   # must be >= 3.10
pip install -e .
```

**Verification**:

```bash
stang --version
```

## `Checksum mismatch: container may be corrupted.`

**Cause**: the trailer doesn't match the payload (plain SHA-256 mode).

**Solution**: restore the file from a known-good copy. If you created it yourself, re-encode
from the source JSON.

## `Authentication failed: wrong passphrase or corrupted data.`

**Cause**: the AEAD trailer could not be verified — either the passphrase is wrong or the file
was modified after creation.

**Solution**: double-check the passphrase (`--passphrase-env`/`--passphrase-file`). If the
passphrase is certainly correct, treat the file as corrupt/tampered and restore it.

## `Integrity check failed: bad key or corrupted data.`

**Cause**: the HMAC trailer did not verify.

**Solution**: supply the correct `--key-env` / `--key-file`. Otherwise treat the file as untrusted.

## `ENCRYPTED` / exit code 2 from `stang verify`

**Cause**: the file is encrypted or HMAC-keyed and no credentials were supplied.

**Solution**: pass `--passphrase-env`/`--passphrase-file` (encrypted) or `--key-env`/`--key-file`
(HMAC). The `2` exit code means "cannot verify yet", not "invalid".

## `Invalid magic bytes`

**Cause**: not an `.stg` file (or a text/JSON file renamed to `.stg`).

**Solution**: check the input file with `file your.stg` and fix the pipeline that produced it.

## `Unsupported STG version`

**Cause**: the file was written by a newer (or older, pre-STG1) tool.

**Solution**: upgrade STANG. If the file is STG1 and you want features like compression, run
`stang convert legacy.stg current.stg --to stg2`.

## `Header extension exceeds the 4 MiB limit.`

**Cause**: the file is corrupt, or not an STG2 file at all.

**Solution**: re-acquire the file; do not raise the limit.

## `File too short` / truncated container

**Cause**: incomplete write or interrupted transfer.

**Solution**: re-encode or re-download the file. Writes via `save_stg` are atomic on POSIX
filesystems when the target is replaced via rename (the CLI writes in place — back up first).

## Port already in use

The STANG CLI uses no ports. This comes from an extended server deployment; change the port in configuration.

## Permission denied

```bash
ls -l data.stg
chmod 600 data.stg
```

## Node timeout

Increase the node `timeout` in its configuration or optimize the node implementation.

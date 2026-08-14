# Troubleshooting

## STANG fails to start

**Cause**: Python version is too old or the package is not installed.

**Solution**:

```bash
python --version  # must be >= 3.10
pip install -e .
```

**Verification**:

```bash
stang --version
```

## Port already in use

STANG CLI does not use ports. This error comes from an extended server deployment. Change the port in configuration.

## Backend unavailable

For SQLite adapters, ensure the database file path is correct and writable.

## Invalid configuration

Validate YAML syntax and required fields. See `docs/configuration.md`.

## Invalid route

Ensure node IDs are unique and referenced correctly.

## Node timeout

Increase timeout or optimize the node implementation.

## Database connection failed

Check connection string, permissions, and that the database service is running.

## Permission denied

Check file ownership and mode:

```bash
ls -l data.stg
chmod 600 data.stg
```

## Corrupted configuration

Restore from version control or a known-good backup.

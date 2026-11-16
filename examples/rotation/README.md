# Rotation Example

Demonstrates circular rotation.

```bash
stang encode data.json data.stg --blocks 4 --rotation 0
stang rotate data.stg +2
stang inspect data.stg
```

Rotation is purely logical — the bytes never move, only the `rotation_state` integer in the
header changes. On encrypted containers the file is transparently re-sealed with fresh nonces:

```bash
stang encode secret.json secret.stg --encrypt --passphrase-env STANG_PASSPHRASE
stang rotate secret.stg +1 --passphrase-env STANG_PASSPHRASE
```

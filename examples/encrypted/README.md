# Encrypted Container Example

Create and read an AEAD-sealed `.stg` file.

```bash
export STANG_PASSPHRASE="$(stang keygen)"
stang encode input.json secret.stg --encrypt --passphrase-env STANG_PASSPHRASE
stang inspect secret.stg                                  # header view only, no schema leak
stang verify secret.stg --passphrase-env STANG_PASSPHRASE
stang decode secret.stg out.json --passphrase-env STANG_PASSPHRASE
```

Programmatic version:

```python
from stang import save_stg, load_stg

records = [{"id": 1, "secret": "hidden"}]
save_stg("secret.stg", records, passphrase="correct horse battery staple", compress=True)
assert load_stg("secret.stg", passphrase="correct horse battery staple") == records
```

The trailer is HMAC-SHA256 over the whole payload (Encrypt-then-MAC); a wrong passphrase fails
verification before any block is examined.

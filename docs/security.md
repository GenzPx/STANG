# Security

## Authentication & Integrity

- **Plain containers** (default): SHA-256 trailer. Detects accidental corruption. Anyone can read and verify.
- **HMAC containers** (`--hmac`): HMAC-SHA256 trailer. Authenticity for shared files; readers holding the key can detect tampering. Data is still readable by anyone.
- **Encrypted containers** (`--encrypt`): AEAD construction (PBKDF2-HMAC-SHA256, 100k iterations → enc-master + MAC key; HMAC-SHA256 counter-mode stream; per-block nonce; Encrypt-then-MAC trailer). Confidentiality + authenticity of block payloads.

In all modes, verification happens **before** any payload byte is parsed, and a failing file never yields partial records.

## What is visible without credentials

Header, salt, block count, rotation state, sizes, and **schema field names**. Block contents are opaque (and encrypted) only in encrypted mode. If field names are sensitive, use opaque names.

## Authorization

File permissions are enforced by the operating system. Ensure `.stg` files are readable only by authorized users (`chmod 600`).

## Secret Management

- Never pass secrets as command-line arguments — they leak into shell history and process lists.
- Use `--passphrase-env`, `--passphrase-file`, `--key-env`, `--key-file`, or the interactive prompt.
- `stang keygen` generates 256-bit random passphrases.
- Keep STANG tools updated; the AEAD construction is versioned as part of STG2.

## Configuration Security

Use `.env.example` as a template. Never commit `.env` files.

## Network Exposure

The core library does not open network sockets. If you expose STANG over HTTP, apply standard web security practices and request-size limits.

## Logging Sensitive Information

Do not log full records, passphrases, or integrity keys.

## Input Validation

STANG validates file structure, bounds and the trailer. It does not validate application-level business rules — do that in your own layer.

## Dependency Security

The runtime has no third-party dependencies (Python stdlib only). Audit `[dev]` dependencies regularly (`pip list --outdated`), and keep the web toolchain (`npm audit`) clean.

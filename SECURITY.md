# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | Yes       |
| 1.0.x   | Legacy (security fixes on request) |

## Reporting a Vulnerability

If you discover a security vulnerability in STANG, please report it responsibly.

**Do not open a public issue for sensitive vulnerabilities.**

Instead, contact the maintainers privately. Provide:

- A description of the vulnerability.
- Steps to reproduce.
- Possible impact.
- Suggested mitigation, if any.

We will acknowledge receipt within 72 hours and work toward a resolution.

## Security Design

- **Integrity**: every container ends with a trailer digest over all preceding bytes.
- **Authenticity**: HMAC-SHA256 mode detects tampering for shared files.
- **Confidentiality**: encrypted containers use a PBKDF2-HMAC-SHA256 derived, per-block
  HMAC-SHA256 counter-mode stream with an Encrypt-then-MAC trailer. Wrong passphrases fail
  at the trailer check before any block is examined.
- **Bounds**: readers validate magic, version, flags combination, extension size and every
  region offset before slicing; trailing garbage is rejected.
- **Strict flags**: unknown flag bits (STG2) and any non-zero flags (STG1) are rejected, not
  silently ignored.
- **Strict JSON**: NaN/Infinity literals are not valid JSON and are rejected on both read and
  write paths.
- **No partial data**: verification happens before payload parsing; failures yield no records.
- Verification never depends on network access. The core library performs no network I/O.

## What is visible without a passphrase

Header, salt, block count, sizes, rotation state, and schema field names. Use opaque field
names if that is acceptable exposure; otherwise do not store the data in `.stg` at rest.

## Best Practices

- Keep STANG updated.
- Never pass secrets as command-line arguments; use `--passphrase-env` / `--passphrase-file` / `--key-env` / `--key-file`.
- `chmod 600` sensitive `.stg` files.
- `stang verify` files received from third parties before relying on them.
- Treat `Authentication failed` as an integrity signal: either you typed the wrong passphrase or the file was modified.

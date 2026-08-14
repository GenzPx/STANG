# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

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

- STANG does not obfuscate data or attempt to bypass security scanners.
- Checksums detect accidental corruption, not malicious tampering.
- No network communication is performed by the core library.
- The CLI operates only on files explicitly provided by the user.

## Best Practices

- Keep STANG updated.
- Do not store unencrypted secrets in `.stg` files.
- Verify file integrity with `stang verify` when receiving files from others.

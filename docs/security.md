# Security

## Authentication

STANG core does not implement authentication. Wrap it in an application that handles identity if needed.

## Authorization

File permissions are enforced by the operating system. Ensure `.stg` files are readable only by authorized users.

## Secret Management

Never store passwords, keys, or tokens in `.stg` files without encryption. Use environment variables or a secrets manager.

## Configuration Security

Use `.env.example` as a template. Never commit `.env` files.

## Network Exposure

The core library does not open network sockets. If you expose STANG over HTTP, follow standard web security practices.

## Database Permissions

When using adapters, use least-privilege database accounts.

## Logging Sensitive Information

Do not log full records or checksums of sensitive data.

## Input Validation

STANG validates file structure and checksums. It does not validate application-level business rules.

## Request Limits

For HTTP-facing deployments, set request size and timeout limits.

## Dependency Security

The runtime has no third-party dependencies. Audit `[dev]` dependencies regularly.

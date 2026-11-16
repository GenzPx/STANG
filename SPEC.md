# STANG File Format Specification

## Version

This document describes STG format version **2** (current) and version **1** (legacy).
Readers MUST auto-detect the version from the magic bytes.

- `STG2` — version 2. Current. Adds compression, authenticated encryption and HMAC integrity.
- `STG1` — version 1. Legacy. SHA-256 checksum only. Still readable and writable by all tools.

## Overview

A `.stg` file is a self-describing, versioned, checksummed container for structured records.
The format uses only standard-library-compatible primitives (canonical JSON, zlib, SHA-256,
HMAC-SHA256, PBKDF2-HMAC-SHA256).

## Design Goals

- **Deterministic**: same input and parameters produce identical bytes (compression level and
  nonces/salt aside — see [Determinism](#determinism)).
- **Versioned**: tools detect and reject unsupported format versions.
- **Self-describing**: a schema travels with the data.
- **Integrity-checked**: a trailing digest covers every preceding byte.
- **Authenticated**: optional HMAC-SHA256 integrity or full AEAD-style encryption.
- **Round-trippable**: `decode(encode(data)) == data` semantically.
- **Rotational**: a logical rotation state is stored in the header; reading starts there.

## File Layout — STG2

```text
┌─────────────────────────────────────┐
│ Header (fixed 32 bytes)             │
├─────────────────────────────────────┤
│ Header Extension (JSON, UTF-8)      │
├─────────────────────────────────────┤
│ Block Entry 0 (u32be len + blob)    │
├─────────────────────────────────────┤
│ Block Entry 1                       │
├─────────────────────────────────────┤
│ ...                                 │
├─────────────────────────────────────┤
│ Block Entry N                       │
├─────────────────────────────────────┤
│ Trailer (32 bytes)                  │
└─────────────────────────────────────┘
```

All integers are **big-endian**.

## Header — STG2

| Field | Offset | Size | Type | Description |
|-------|--------|------|------|-------------|
| magic | 0 | 4 | bytes | `STG2` (0x53544732) |
| version | 4 | 1 | uint8 | `2` |
| flags | 5 | 1 | uint8 | see [Flags](#flags) |
| rotation_state | 6 | 4 | uint32be | Logical rotation index (normalized mod block_count) |
| ext_len | 10 | 4 | uint32be | Length of the header extension in bytes (≤ 4 MiB) |
| block_count | 14 | 2 | uint16be | Number of block entries (informational; the entries are authoritative) |
| salt | 16 | 16 | bytes | Random per container; PBKDF2 salt when encrypted, zeroes otherwise |

Packed as `!4sBBIIH16s` (C struct format). Total: **32 bytes**.

## Flags

| Bit | Name | Meaning |
|-----|------|---------|
| 0x01 | `COMPRESSED` | Each block's plaintext is zlib (RFC 1950) compressed |
| 0x02 | `ENCRYPTED` | Blocks are sealed with the AEAD construction in [Encryption](#encryption) |
| 0x04 | `HMAC` | Trailer is HMAC-SHA256 with a caller-supplied integrity key |

`0x02` and `0x04` are mutually exclusive (`0x02` already authenticates). Unknown bits MUST be
ignored by readers and MUST be written as zero.

## Header Extension

A UTF-8 canonical JSON object. Required keys:

```json
{
  "schema": {
    "fields": {
      "id": "integer",
      "meta.value": "float"
    }
  }
}
```

When the container is encrypted, an additional key is present:

```json
{
  "kdf": { "name": "pbkdf2-sha256", "iterations": 100000, "key_len": 64 }
}
```

Extensions MAY carry additional keys. Readers MUST NOT reject unknown keys.
The extension is not encrypted; **schema field names are visible without a passphrase**.

## Data Blocks

Block entries are length-prefixed:

```text
offset  size  field
0       4     blob_len (uint32be)
4       N     blob
```

`blob` decodes as follows:

1. If `flags & 0x02`: the first 16 bytes are the block nonce; the remainder is the ciphertext.
   Decrypt with the AEAD construction below. The plaintext length is `blob_len - 16`.
2. If `flags & 0x01`: zlib-decompress the (decrypted) plaintext (RFC 1950; any compliant
   decompressor is accepted — the compression level is the writer's choice).
3. The result is UTF-8 canonical JSON: an array of the block's records.

Records are distributed **round-robin by record index** at encode time:
record `i` lands in block `i mod block_count`. Empty blocks are legal and MUST be preserved.

## Schema

Dot-flattened type map of record fields. Supported types:

```text
string · integer · float · boolean · null · array · object · any
```

- Nested objects flatten with dot notation (`meta.city`).
- Types are merged across **all** records.
- `integer + float → float`; conflicting kinds widen to `any`; `null` yields to any other type.

## Trailer

32 bytes, computed over every preceding byte (`payload`):

| Mode | Condition | Digest |
|------|-----------|--------|
| Plain | neither `0x02` nor `0x04` | `SHA-256(payload)` |
| HMAC | `flags & 0x04` | `HMAC-SHA256(integrity_key, payload)` |
| AEAD | `flags & 0x02` | `HMAC-SHA256(mac_key, payload)` (Encrypt-then-MAC) |

Verification MUST use constant-time comparison and MUST happen **before** any payload byte is
trusted. On mismatch, readers MUST raise and return no records.

## Encryption

When `flags & 0x02`:

```text
salt      := 16 random bytes from the header
keys      := PBKDF2-HMAC-SHA256(passphrase, salt, iterations=100_000, dkLen=64)
            = enc_master (32 B) ‖ mac_key (32 B)
block_key := HMAC-SHA256(enc_master, "stang-blk" ‖ u32be(block_index) ‖ nonce)
keystream := HMAC-SHA256(block_key, u64be(counter)) for counter = 0, 1, 2, …
ciphertext:= plaintext XOR keystream
blob      := nonce (16 B) ‖ ciphertext
```

- The passphrase is UTF-8 encoded. Empty passphrases MUST be rejected.
- Each block carries its own random 16-byte nonce.
- The trailer is `HMAC-SHA256(mac_key, payload)` — Encrypt-then-MAC.
- Wrong passphrases are indistinguishable from tampering: readers fail at the trailer check
  without examining any block.

## Canonical JSON

"Canonical JSON" throughout this document means:

- UTF-8, no whitespace between tokens (`,` and `:` separators).
- Object keys sorted lexicographically (by Unicode code points), recursively.
- Numbers: integers in plain decimal; non-integers in the shortest round-trip form
  (`9.5`, `3.25`); exponents with a leading `0` in the fractional exponent (`1e-07`).
- Strings: minimal escaping; control characters as `\uXXXX` (lowercase hex); short escapes
  `\b \f \n \r \t \" \\` used where applicable; all other characters emitted raw as UTF-8.
- `ensure_ascii=False` equivalent — non-ASCII characters are never `\uXXXX`-escaped.

Writers MUST use canonical JSON for schema, extension, blocks and the v1 block table.

## Determinism

- Plain (unencrypted, uncompressed) containers are byte-deterministic: same input records,
  `block_count`, `rotation_state` and version → identical bytes.
- Compressed containers depend on the zlib implementation and level (level 9 is conventional).
- Encrypted containers are never byte-deterministic (fresh salt, fresh nonces).
  Test vectors pin `salt` and `nonces` explicitly (see `tests/fixtures/` and `scripts/conformance.mjs`).

## Bounds and Robustness

Readers MUST:

- reject files shorter than `header + 32` bytes;
- reject `magic` values other than `STG1`/`STG2`;
- reject unsupported `version` values;
- reject `ext_len > 4 MiB`;
- reject `0x02 | 0x04` flag combinations;
- bounds-check every region before slicing (schema/extension, table, blocks, trailer);
- reject trailing bytes after the last block;
- verify the trailer before parsing any payload content;
- never return partially decoded records on failure.

## File Layout — STG1 (legacy)

```text
┌─────────────────────────────────────┐
│ Header (fixed 14 bytes, !4sBBII)    │
├─────────────────────────────────────┤
│ Schema (JSON, UTF-8)                │
├─────────────────────────────────────┤
│ Block Table (JSON, UTF-8)           │
├─────────────────────────────────────┤
│ Data Block 0 (JSON, UTF-8)          │
├─────────────────────────────────────┤
│ ...                                 │
├─────────────────────────────────────┤
│ Checksum (32 bytes, SHA-256)        │
└─────────────────────────────────────┘
```

| Field | Size | Type | Description |
|-------|------|------|-------------|
| magic | 4 | bytes | `STG1` |
| version | 1 | uint8 | `1` |
| flags | 1 | uint8 | reserved, must be 0 on write |
| rotation_state | 4 | uint32be | logical rotation index |
| schema_len | 4 | uint32be | length of schema JSON |

The block table is a JSON array of `[offset, size]` absolute payload offsets (from byte 0 of
the payload, i.e. the start of the header). Offsets are written after iterating to a fixed
point, because the table length depends on the offsets it contains. The trailer is SHA-256
over everything before it. STG1 has **no** compression or crypto support.

## Security Notes

STANG is a storage container, not a security boundary. Readers must treat all input as
untrusted: apply the bounds checks above, verify before parsing, and never evaluate content.
The AEAD construction provides confidentiality and authenticity for block payloads only;
the header, salt, extension (schema field names) and block metadata are visible to anyone
who holds the file. Use opaque field names if that is sensitive.

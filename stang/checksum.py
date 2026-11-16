"""Integrity checking for STG containers."""

from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stang.container import STGContainer


def normalize_key(key: bytes | str | None) -> bytes | None:
    """Normalize an optional secret key into UTF-8 bytes."""
    if key is None:
        return None
    if isinstance(key, bytes):
        return key
    if isinstance(key, str):
        return key.encode("utf-8")
    raise TypeError("Key must be bytes, str, or None.")


def compute_checksum(payload: bytes, key: bytes | str | None = None) -> bytes:
    """Compute a deterministic 32-byte digest for ``payload``.

    Args:
        payload: Raw bytes to checksum.
        key: Optional HMAC secret. When absent, a plain SHA-256 digest is returned.

    Returns:
        A 32-byte digest.
    """
    raw_key = normalize_key(key)
    if raw_key is None:
        return hashlib.sha256(payload).digest()
    return hmac.new(raw_key, payload, hashlib.sha256).digest()


def verify_checksum(payload: bytes, expected: bytes, key: bytes | str | None = None) -> bool:
    """Verify ``payload`` against an expected digest using constant-time comparison."""
    actual = compute_checksum(payload, key)
    return hmac.compare_digest(actual, expected)


def container_checksum(container: STGContainer, key: bytes | str | None = None) -> bytes:
    """Compute the trailer digest for an unencrypted ``container``.

    Encrypted containers have no stable plaintext digest (the payload includes
    fresh nonces), so use :meth:`STGContainer.serialize` for those.
    """
    from stang.errors import EncryptionError

    if container.is_encrypted:
        raise EncryptionError(
            "Encrypted containers have no stable plaintext checksum; use serialize()."
        )
    from stang.container import FLAG_HMAC
    from stang.errors import IntegrityError

    resolved = normalize_key(key) if key is not None else container._integrity_key
    if container.flags & FLAG_HMAC and resolved is None:
        raise IntegrityError("This container requires an integrity key.")
    return compute_checksum(container.serialize_payload(), resolved)

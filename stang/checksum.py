"""Integrity checking for STG containers."""

from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stang.container import STGContainer


def compute_checksum(payload: bytes, key: bytes | None = None) -> bytes:
    """Compute a deterministic checksum for *payload*.

    Parameters
    ----------
    payload:
        Raw bytes to checksum.
    key:
        Optional HMAC secret. When absent, a plain SHA-256 digest is returned.

    Returns
    -------
    bytes
        32-byte digest.
    """
    if key is None:
        return hashlib.sha256(payload).digest()
    return hmac.new(key, payload, hashlib.sha256).digest()


def verify_checksum(payload: bytes, expected: bytes, key: bytes | None = None) -> bool:
    """Verify *payload* against an expected digest.

    Uses constant-time comparison to mitigate timing attacks.
    """
    actual = compute_checksum(payload, key)
    return hmac.compare_digest(actual, expected)


def container_checksum(container: "STGContainer", key: bytes | None = None) -> bytes:
    """Compute the checksum over the serialized data blocks of *container*."""
    return compute_checksum(container.serialize_payload(), key)

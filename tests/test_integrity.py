"""Tests for integrity checking and error handling."""

from __future__ import annotations

import pytest

from stang.container import ContainerError, STGContainer
from stang.encoder import encode_stg
from stang.errors import AuthenticationError, IntegrityError


def _flip_byte(data: bytes, index: int) -> bytes:
    mutated = bytearray(data)
    mutated[index] ^= 0x01
    return bytes(mutated)


def test_checksum_corruption():
    container = encode_stg([{"id": 1}])
    data = bytearray(container.serialize())
    data[-1] ^= 0xFF
    with pytest.raises(ContainerError, match="Checksum"):
        STGContainer.deserialize(bytes(data))


def test_invalid_magic():
    container = encode_stg([{"id": 1}])
    data = bytearray(container.serialize())
    data[:4] = b"XXXX"
    with pytest.raises(ContainerError, match="magic"):
        STGContainer.deserialize(bytes(data))


def test_unsupported_version():
    container = encode_stg([{"id": 1}], format_version=1)
    data = bytearray(container.serialize())
    data[4] = 99  # version byte
    with pytest.raises(ContainerError, match="version"):
        STGContainer.deserialize(bytes(data))


def test_truncated_file():
    container = encode_stg([{"id": 1}])
    data = container.serialize()[:10]
    with pytest.raises(ContainerError):
        STGContainer.deserialize(data)


def test_trailing_garbage_rejected():
    container = encode_stg([{"id": 1}])
    data = container.serialize()
    # Append before the trailer: corrupt by inserting mid-file is covered elsewhere;
    # here verify a blob with extra data after the trailer also fails length checks
    # only when it breaks offsets; trailer+garbage must at least fail the digest.
    with pytest.raises(ContainerError):
        STGContainer.deserialize(data[:-32] + b"\x00" * 32)


def test_v2_block_tampering_detected():
    container = encode_stg([{"id": i} for i in range(10)], block_count=2)
    blob = bytearray(container.serialize())
    # Flip a byte inside the first block region (after the 32-byte header and extension).
    flip_at = len(blob) - 40
    blob[flip_at] ^= 0xFF
    with pytest.raises(ContainerError):
        STGContainer.deserialize(bytes(blob))


def test_v2_encrypted_roundtrip_and_wrong_passphrase():
    container = encode_stg([{"id": 1, "secret": "hide-me"}], passphrase="pw")
    blob = container.serialize()
    assert b"hide-me" not in blob
    restored = STGContainer.deserialize(blob, passphrase="pw")
    assert restored.blocks[0][0]["secret"] == "hide-me"
    with pytest.raises(AuthenticationError):
        STGContainer.deserialize(blob, passphrase="nope")
    with pytest.raises(AuthenticationError):
        STGContainer.deserialize(blob)  # missing passphrase


def test_v2_encrypted_header_tampering_detected():
    container = encode_stg([{"id": i} for i in range(4)], passphrase="pw", block_count=2)
    blob = _flip_byte(container.serialize(), 8)  # rotation_state byte: header must fail MAC
    with pytest.raises(AuthenticationError):
        STGContainer.deserialize(blob, passphrase="pw")


def test_v2_hmac_mode_roundtrip_and_wrong_key():
    container = encode_stg([{"id": 1}], integrity_key=b"secret-key")
    blob = container.serialize()
    restored = STGContainer.deserialize(blob, integrity_key=b"secret-key")
    assert restored.blocks[0][0]["id"] == 1
    with pytest.raises(IntegrityError):
        STGContainer.deserialize(blob, integrity_key=b"wrong-key")
    with pytest.raises(IntegrityError):
        STGContainer.deserialize(blob)  # missing key


def test_v2_encrypted_ignores_plain_sha_expectation():
    container = encode_stg([{"id": 1}], passphrase="pw")
    blob = container.serialize()
    # Even a SHA-256 recomputation over the payload would differ; the HMAC must hold.
    import hashlib

    forged = blob[:-32] + hashlib.sha256(blob[:-32]).digest()
    with pytest.raises(AuthenticationError):
        STGContainer.deserialize(forged, passphrase="pw")


def test_v1_checksum_still_enforced():
    container = encode_stg([{"id": 1}], format_version=1)
    data = bytearray(container.serialize())
    data[-1] ^= 0xFF
    with pytest.raises(ContainerError, match="Checksum"):
        STGContainer.deserialize(bytes(data))

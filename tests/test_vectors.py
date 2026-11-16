"""Golden test vectors shared with the JavaScript STANG implementation.

The fixtures in ``tests/fixtures/`` were generated with this implementation
and are validated byte-for-byte by the browser codec (see
``scripts/conformance.mjs``). They pin:

* the STG2 wire layout (header, extension, blocks, trailer);
* zlib compression compatibility with ``CompressionStream('deflate')``;
* the PBKDF2/HMAC key-derivation and stream-cipher construction;
* canonical JSON serialization.
"""

from __future__ import annotations

import json
from pathlib import Path

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.encoder import encode_stg

FIXTURES = Path(__file__).parent / "fixtures"
PASSPHRASE = "secret-stang-key"
SALT = bytes(range(16))
NONCES = [bytes([0xA0 + i] * 16) for i in range(3)]
PLAIN_SALT = bytes(range(16))
PLAIN_NONCES = [bytes([0xB0 + i] * 16) for i in range(3)]


def _records() -> list[dict]:
    return json.loads((FIXTURES / "golden.json").read_text(encoding="utf-8"))


def test_golden_plain_deserializes():
    blob = (FIXTURES / "golden_plain.stg").read_bytes()
    container = STGContainer.deserialize(blob)
    assert container.format_version == 2
    assert container.block_count == 3
    assert container.rotation_state == 1
    assert decode_stg(container) == _records()


def test_golden_plain_reserializes_byte_for_byte():
    blob = (FIXTURES / "golden_plain.stg").read_bytes()
    container = STGContainer.deserialize(blob)
    assert container.serialize() == blob


def test_golden_plain_matches_fresh_encode():
    blob = (FIXTURES / "golden_plain.stg").read_bytes()
    fresh = encode_stg(_records(), block_count=3, rotation_state=1)
    assert fresh.serialize() == blob


def test_golden_encrypted_deserializes():
    blob = (FIXTURES / "golden_encrypted.stg").read_bytes()
    assert b"Genz" not in blob  # plaintext must not leak
    container = STGContainer.deserialize(blob, passphrase=PASSPHRASE)
    assert container.is_encrypted
    assert container.is_compressed
    assert container.rotation_state == 1
    assert decode_stg(container) == _records()


def test_golden_encrypted_reproduces_with_pinned_salt_and_nonces():
    fresh = encode_stg(
        _records(),
        block_count=3,
        rotation_state=1,
        passphrase=PASSPHRASE,
        compress=True,
    )
    blob = fresh.serialize(passphrase=PASSPHRASE, salt=SALT, block_nonces=NONCES)
    assert blob == (FIXTURES / "golden_encrypted.stg").read_bytes()


def test_golden_encrypted_rejects_wrong_passphrase():
    blob = (FIXTURES / "golden_encrypted.stg").read_bytes()
    try:
        STGContainer.deserialize(blob, passphrase="wrong")
    except Exception as exc:  # AuthenticationError
        assert "Authentication failed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("wrong passphrase was accepted")


def test_golden_encrypted_plain_roundtrip():
    blob = (FIXTURES / "golden_encrypted_plain.stg").read_bytes()
    assert b"Genz" not in blob
    container = STGContainer.deserialize(blob, passphrase=PASSPHRASE)
    assert not container.is_compressed
    assert container.is_encrypted
    assert decode_stg(container) == _records()


def test_golden_encrypted_plain_reproduces_with_pinned_salt_and_nonces():
    fresh = encode_stg(
        _records(),
        block_count=3,
        rotation_state=1,
        passphrase=PASSPHRASE,
    )
    blob = fresh.serialize(passphrase=PASSPHRASE, salt=PLAIN_SALT, block_nonces=PLAIN_NONCES)
    assert blob == (FIXTURES / "golden_encrypted_plain.stg").read_bytes()

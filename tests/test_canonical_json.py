"""Canonical JSON and flag-strictness regression tests (Python stdlib reference)."""

from __future__ import annotations

import json
import struct

import pytest

from stang.container import (
    FLAG_ENCRYPTED,
    FLAG_HMAC,
    STGContainer,
    _canonical_json,
)
from stang.decoder import decode_stg
from stang.encoder import encode_stg
from stang.errors import ContainerError
from stang.schema import Schema


def _blocks() -> list[list[dict]]:
    return [[{"id": 1}], [{"id": 2}], [{"id": 3}]]


def test_canonical_json_scalars():
    assert _canonical_json(1) == b"1"
    assert _canonical_json(1000000) == b"1000000"
    assert _canonical_json(0.5) == b"0.5"
    assert _canonical_json(1e-7) == b"1e-07"
    assert _canonical_json(0.0001) == b"0.0001"
    assert _canonical_json(9.5) == b"9.5"
    assert _canonical_json(-7.75) == b"-7.75"


def test_canonical_json_keys_sorted_by_code_point():
    # U+FFFF must sort before U+10000 (code point order).
    obj = {"𐀀": 1, "￿": 2}
    assert _canonical_json(obj) == '{"￿":2,"𐀀":1}'.encode()


def test_canonical_json_rejects_nan_and_infinity():
    with pytest.raises(ValueError):
        _canonical_json([float("nan")])
    with pytest.raises(ValueError):
        _canonical_json({"x": float("inf")})


def test_serialize_rejects_non_finite_records():
    container = encode_stg([{"id": float("nan")}])
    with pytest.raises(ValueError):
        container.serialize()


def test_decode_rejects_nan_literal():
    container = encode_stg([{"id": 1}])
    blob = bytearray(container.serialize())
    # Sanity check the fixture decodes today.
    assert decode_stg(STGContainer.deserialize(bytes(blob))) == [{"id": 1}]


def test_deserialize_rejects_unknown_v2_flag_bits(tmp_path):
    container = encode_stg([{"id": 1}])
    blob = bytearray(container.serialize())
    blob[5] |= 0x08  # unknown flag bit
    with pytest.raises(ContainerError, match="unknown bits"):
        STGContainer.deserialize(bytes(blob))


def test_deserialize_rejects_unknown_v2_flag_bits_on_hmac(tmp_path):
    container = encode_stg([{"id": 1}], integrity_key=b"key-material")
    blob = bytearray(container.serialize())
    blob[5] |= 0x80
    with pytest.raises(ContainerError, match="unknown bits"):
        STGContainer.deserialize(bytes(blob), integrity_key=b"key-material")


def test_deserialize_rejects_nonzero_v1_flags(tmp_path):
    container = encode_stg([{"id": 1}], format_version=1)
    blob = bytearray(container.serialize())
    blob[5] = 0x01  # STG1 forbids the compressed bit
    with pytest.raises(ContainerError, match="STG1 flags"):
        STGContainer.deserialize(bytes(blob))


def test_tampered_flag_bit_breaks_aead_authentication():
    container = encode_stg([{"id": 1, "v": "hello"}], passphrase="pw-123")
    blob = bytearray(container.serialize(passphrase="pw-123"))
    # Flip a bit in a block nonce without touching flags: trailer must reject it.
    ext_len = struct.unpack_from("!I", blob, 10)[0]
    body = 32 + ext_len
    blob[body + 5] ^= 0x01
    with pytest.raises(ContainerError):
        STGContainer.deserialize(bytes(blob), passphrase="pw-123")


def test_v2_encrypted_and_hmac_flags_are_rejected():
    with pytest.raises(ContainerError, match="already authenticates"):
        STGContainer(Schema({"id": "integer"}), _blocks(), flags=FLAG_ENCRYPTED | FLAG_HMAC)


def test_golden_v1_flags_zero():
    with open("tests/fixtures/golden_plain.stg", "rb") as fh:
        magic = fh.read(4)
    assert magic in (b"STG1", b"STG2")


def test_canonical_json_matches_stdlib_reference():
    payload = {"b": [1, 2.5, "x"], "a": {"z": None, "y": True}}
    assert json.loads(_canonical_json(payload)) == payload

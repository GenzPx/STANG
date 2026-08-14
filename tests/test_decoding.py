"""Tests for STG decoding."""

from stang.decoder import decode_stg, load_stg
from stang.encoder import encode_stg, save_stg


def test_roundtrip():
    records = [{"id": 1, "name": "Genz", "value": "example"}]
    container = encode_stg(records)
    decoded = decode_stg(container)
    assert decoded == records


def test_roundtrip_file(tmp_path):
    records = [{"id": i, "name": f"n{i}"} for i in range(50)]
    path = tmp_path / "data.stg"
    save_stg(path, records, block_count=4, rotation_state=2)
    decoded = load_stg(path)
    assert decoded == records


def test_decode_returns_original_data():
    records = [{"id": i} for i in range(10)]
    container = encode_stg(records, block_count=4, rotation_state=2)
    decoded = decode_stg(container)
    assert decoded == records

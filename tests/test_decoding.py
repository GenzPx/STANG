"""Tests for decoding and round-tripping containers."""

from __future__ import annotations

from stang.container import STGContainer
from stang.decoder import decode_stg, decode_to_json, load_stg
from stang.encoder import encode_stg, save_stg


def test_roundtrip():
    records = [{"id": 1, "name": "Genz", "value": "example"}]
    container = encode_stg(records)
    decoded = decode_stg(container)
    assert decoded == records


def test_roundtrip_file(tmp_path):
    records = [{"id": i, "name": f"n{i}"} for i in range(50)]
    path = tmp_path / "data.stg"
    save_stg(path, records, block_count=4, rotation_state=1)
    loaded = load_stg(path)
    assert loaded == records


def test_decode_returns_original_data():
    records = [{"id": i} for i in range(10)]
    container = encode_stg(records, block_count=4, rotation_state=2)
    assert decode_stg(container) == records


def test_v1_roundtrip_explicit(tmp_path):
    records = [{"id": i, "nested": {"v": i}} for i in range(7)]
    path = tmp_path / "legacy.stg"
    save_stg(path, records, block_count=3, rotation_state=1, format_version=1)
    data = path.read_bytes()
    assert data[:4] == b"STG1"
    loaded = load_stg(path)
    assert loaded == records


def test_v1_bytes_are_readable(tmp_path):
    """Byte-level check: a hand-built v1 container decodes correctly."""
    records = [{"id": 1, "name": "Genz"}, {"id": 2, "name": "Ana"}]
    path = tmp_path / "legacy.stg"
    save_stg(path, records, block_count=2, format_version=1)
    container = STGContainer.deserialize(path.read_bytes())
    assert container.format_version == 1
    assert container.magic == b"STG1"
    assert decode_stg(container) == records


def test_mixed_format_detection():
    records = [{"id": 1}]
    v1 = encode_stg(records, format_version=1).serialize()
    v2 = encode_stg(records, format_version=2).serialize()
    assert STGContainer.deserialize(v1).format_version == 1
    assert STGContainer.deserialize(v2).format_version == 2


def test_encrypted_roundtrip_preserves_data():
    records = [{"id": i, "note": f"note-{i}"} for i in range(30)]
    container = encode_stg(records, passphrase="pw", compress=True, block_count=4)
    blob = container.serialize()
    restored = STGContainer.deserialize(blob, passphrase="pw")
    assert decode_stg(restored) == records


def test_load_stg_with_passphrase(tmp_path):
    records = [{"id": 1, "secret": "s3cret"}]
    path = tmp_path / "secret.stg"
    save_stg(path, records, passphrase="pw")
    assert load_stg(path, passphrase="pw") == records


def test_decode_to_json_is_deterministic():
    records = [{"id": 2, "name": "foo"}, {"id": 1, "name": "bar"}]
    container = encode_stg(records)
    assert decode_to_json(container) == decode_to_json(container)
    assert b'"id":1' in decode_to_json(container)  # sorted keys, compact

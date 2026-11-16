"""Tests for record encoding and schema inference."""

from __future__ import annotations

import json

import pytest

from stang.container import FLAG_COMPRESSED, FLAG_ENCRYPTED, STGContainer
from stang.encoder import encode_from_json, encode_stg
from stang.schema import Schema, SchemaError


def test_empty_dataset():
    container = encode_stg([])
    assert container.block_count == 4
    assert container.record_count == 0
    assert container.schema.fields == {}


def test_single_record():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    assert container.record_count == 1
    data = container.serialize()
    assert STGContainer.deserialize(data).record_count == 1


def test_many_records():
    records = [{"id": i, "value": f"v{i}"} for i in range(1000)]
    container = encode_stg(records, block_count=8)
    assert container.record_count == 1000
    assert container.block_count == 8


def test_nested_objects():
    records = [{"id": 1, "meta": {"a": 1, "b": "x"}}]
    container = encode_stg(records)
    assert container.schema.fields["meta.a"] == "integer"
    assert container.schema.fields["meta.b"] == "string"


def test_arrays():
    records = [{"id": 1, "tags": ["a", "b", "c"]}]
    container = encode_stg(records)
    assert container.schema.fields["tags"] == "array"


def test_mixed_record_types_merge():
    records = [{"id": 1}, {"id": 2, "extra": "now-present"}]
    container = encode_stg(records)
    assert container.schema.fields["id"] == "integer"
    assert container.schema.fields["extra"] == "string"


def test_numeric_widening_int_to_float():
    schema = Schema.infer_many([{"v": 1}, {"v": 2.5}])
    assert schema.fields["v"] == "float"


def test_conflicting_types_become_any():
    schema = Schema.infer_many([{"v": "text"}, {"v": 1}])
    assert schema.fields["v"] == "any"


def test_validate_record_rejects_wrong_type():
    schema = Schema({"id": "integer"})
    schema.validate_record({"id": 1})
    with pytest.raises(SchemaError):
        schema.validate_record({"id": "one"})


def test_unsupported_value_type_rejected():
    with pytest.raises(SchemaError):
        Schema.infer({"bad": object()})


def test_deterministic_encoding():
    data = json.dumps([{"id": 2, "name": "foo"}], sort_keys=True).encode()
    c1 = encode_from_json(data)
    c2 = encode_from_json(data)
    assert c1.serialize() == c2.serialize()


def test_encode_rejects_non_mapping_records():
    with pytest.raises(TypeError):
        encode_stg([1, 2, 3])  # type: ignore[list-item]


def test_encode_rejects_zero_blocks():
    with pytest.raises(ValueError):
        encode_stg([{"id": 1}], block_count=0)


def test_encode_encrypt_and_hmac_are_mutually_exclusive():
    with pytest.raises(ValueError):
        encode_stg([{"id": 1}], passphrase="pw", integrity_key=b"key")


def test_v1_rejects_v2_only_options():
    with pytest.raises(ValueError):
        encode_stg([{"id": 1}], format_version=1, compress=True)
    with pytest.raises(ValueError):
        encode_stg([{"id": 1}], format_version=1, passphrase="pw")


def test_compressed_roundtrip():
    records = [{"id": i, "payload": "x" * 200} for i in range(20)]
    container = encode_stg(records, compress=True)
    assert container.flags & FLAG_COMPRESSED
    blob = container.serialize()
    restored = STGContainer.deserialize(blob)
    assert restored.is_compressed
    assert [list(b) for b in restored.blocks] == [list(b) for b in container.blocks]


def test_encrypted_roundtrip():
    records = [{"id": i, "secret": f"value-{i}"} for i in range(10)]
    container = encode_stg(records, passphrase="pw", compress=True)
    assert container.flags & FLAG_ENCRYPTED
    blob = container.serialize()
    assert b"value-0" not in blob  # plaintext must not leak into the file
    restored = STGContainer.deserialize(blob, passphrase="pw")
    assert [list(b) for b in restored.blocks] == [list(b) for b in container.blocks]


def test_encode_from_json_accepts_single_object():
    container = encode_from_json(b'{"id": 1}')
    assert container.record_count == 1


def test_encode_from_json_rejects_non_object_items():
    with pytest.raises(ValueError):
        encode_from_json(b"[1, 2, 3]")


def test_encode_from_json_rejects_scalar_root():
    with pytest.raises(ValueError):
        encode_from_json(b"42")


def test_encode_from_json_rejects_invalid_json():
    with pytest.raises(ValueError):
        encode_from_json(b"{not json")

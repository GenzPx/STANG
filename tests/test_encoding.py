"""Tests for STG encoding."""

import json

from stang.encoder import encode_from_json, encode_stg
from stang.schema import TYPE_INTEGER, TYPE_STRING


def test_empty_dataset():
    container = encode_stg([])
    assert container.block_count == 4
    assert sum(len(b) for b in container.blocks) == 0


def test_single_record():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    assert container.schema.fields["id"] == TYPE_INTEGER
    assert container.schema.fields["name"] == TYPE_STRING


def test_many_records():
    records = [{"id": i, "value": f"v{i}"} for i in range(1000)]
    container = encode_stg(records, block_count=8)
    assert sum(len(b) for b in container.blocks) == 1000


def test_nested_objects():
    records = [{"id": 1, "meta": {"a": 1, "b": "x"}}]
    container = encode_stg(records)
    assert container.schema.fields["meta.a"] == TYPE_INTEGER
    assert container.schema.fields["meta.b"] == TYPE_STRING


def test_arrays():
    records = [{"id": 1, "tags": ["a", "b", "c"]}]
    container = encode_stg(records)
    assert container.schema.fields["tags"] == "array"


def test_deterministic_encoding():
    data = json.dumps([{"id": 2, "name": "foo"}], sort_keys=True).encode()
    c1 = encode_from_json(data)
    c2 = encode_from_json(data)
    assert c1.serialize() == c2.serialize()

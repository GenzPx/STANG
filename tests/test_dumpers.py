"""Tests for dumper plugins."""

import json

from stang.dumpers import DUMPERS
from stang.encoder import encode_stg


def test_default_block_dumper():
    container = encode_stg([{"id": 1, "name": "Genz"}])
    text = DUMPERS["block"]().dump(container)
    assert "STANG DUMP" in text
    assert "[BLOCK 0]" in text


def test_json_dumper():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    text = DUMPERS["json"]().dump(container)
    assert json.loads(text) == records


def test_csv_dumper():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    text = DUMPERS["csv"]().dump(container)
    assert "id,name" in text or "name,id" in text
    assert "Genz" in text


def test_raw_dumper():
    container = encode_stg([{"id": 1}])
    text = DUMPERS["raw"]().dump(container)
    data = json.loads(text)
    assert data["magic"] == "STG1"
    assert data["version"] == 1

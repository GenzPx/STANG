"""Tests for the dumper plugin system."""

from __future__ import annotations

import csv
import io
import json

from stang.dumpers import DUMPERS
from stang.encoder import encode_stg


def test_default_block_dumper():
    container = encode_stg([{"id": 1, "name": "Genz"}])
    text = DUMPERS["block"]().dump(container)
    assert "STANG DUMP" in text
    assert "BLOCK" in text
    assert "Genz" in text


def test_json_dumper():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    text = DUMPERS["json"]().dump(container)
    assert json.loads(text) == records


def test_ndjson_dumper_is_one_record_per_line():
    records = [{"id": 1}, {"id": 2}, {"id": 3}]
    container = encode_stg(records)
    lines = DUMPERS["ndjson"]().dump(container).splitlines()
    assert [json.loads(line) for line in lines] == records


def test_csv_dumper():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    text = DUMPERS["csv"]().dump(container)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows == [{"id": "1", "name": "Genz"}]


def test_tsv_dumper_uses_tabs():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    text = DUMPERS["tsv"]().dump(container)
    assert "\t" in text.splitlines()[0]


def test_csv_dumper_flattens_nested_values():
    records = [{"id": 1, "meta": {"a": 1, "b": 2}}]
    container = encode_stg(records)
    rows = list(csv.DictReader(io.StringIO(DUMPERS["csv"]().dump(container))))
    assert json.loads(rows[0]["meta"]) == {"a": 1, "b": 2}


def test_markdown_dumper_produces_table():
    records = [{"id": 1, "name": "Genz"}, {"id": 2, "name": "Ana"}]
    container = encode_stg(records)
    text = DUMPERS["markdown"]().dump(container)
    assert text.splitlines()[0].startswith("| id |")
    assert "| --- |" in text
    assert "| 2 | Ana |" in text


def test_markdown_dumper_escapes_pipes():
    records = [{"note": "a|b"}]
    container = encode_stg(records)
    text = DUMPERS["markdown"]().dump(container)
    assert "a\\|b" in text


def test_stats_dumper_reports_blocks():
    records = [{"id": i} for i in range(8)]
    container = encode_stg(records, block_count=4)
    text = DUMPERS["stats"]().dump(container)
    assert "STANG STATS" in text
    assert "records=8" in text
    assert "blocks=4" in text


def test_raw_dumper():
    container = encode_stg([{"id": 1}])
    text = DUMPERS["raw"]().dump(container)
    data = json.loads(text)
    assert data["magic"] == "STG2"
    assert data["format"] == "STG2"


def test_all_registered_dumpers_run():
    records = [{"id": 1, "name": "Genz"}]
    container = encode_stg(records)
    for name, dumper in DUMPERS.items():
        output = dumper().dump(container)
        assert isinstance(output, str), name


def test_empty_container_dumpers():
    container = encode_stg([])
    assert DUMPERS["csv"]().dump(container) == ""
    assert DUMPERS["json"]().dump(container) == "[]"
    assert "no records" in DUMPERS["markdown"]().dump(container).lower()

"""End-to-end tests for the ``stang`` command-line interface."""

from __future__ import annotations

import json
import os

from stang.cli import main


def _write_json(tmp_path, records):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_init_and_status(tmp_path, capsys):
    target = tmp_path / "empty.stg"
    assert main(["init", str(target)]) == 0
    assert target.exists()
    assert main(["status"]) == 0
    assert "STANG" in capsys.readouterr().out


def test_encode_decode_roundtrip_cli(tmp_path, capsys):
    records = [{"id": i, "name": f"n{i}"} for i in range(20)]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    out = tmp_path / "out.json"
    assert main(["encode", str(src), str(stg), "--blocks", "4"]) == 0
    assert main(["decode", str(stg), str(out)]) == 0
    assert json.loads(out.read_text()) == records


def test_encode_v1_and_convert(tmp_path):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    v1 = tmp_path / "legacy.stg"
    v2 = tmp_path / "current.stg"
    assert main(["encode", str(src), str(v1), "--format", "stg1"]) == 0
    assert v1.read_bytes()[:4] == b"STG1"
    assert main(["convert", str(v1), str(v2), "--to", "stg2"]) == 0
    assert v2.read_bytes()[:4] == b"STG2"
    assert main(["verify", str(v2)]) == 0


def test_convert_to_v1_rejects_compressed(tmp_path):
    records = [{"id": 1, "blob": "x" * 500}]
    src = _write_json(tmp_path, records)
    packed = tmp_path / "packed.stg"
    plain = tmp_path / "plain.stg"
    assert main(["encode", str(src), str(packed), "--compress"]) == 0
    assert main(["convert", str(packed), str(plain), "--to", "stg1"]) == 1


def test_verify_encrypted_requires_passphrase(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "secret.stg"
    os.environ["STANG_TEST_PASSPHRASE"] = "pw"
    try:
        assert main(["encode", str(src), str(stg), "--encrypt",
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        capsys.readouterr()
        assert main(["verify", str(stg)]) == 2  # no credentials available
        assert main(["verify", str(stg),
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        assert main(["verify", str(stg), "--passphrase-env", "MISSING_ENV_VAR"]) == 1
    finally:
        del os.environ["STANG_TEST_PASSPHRASE"]


def test_decode_with_passphrase_env(tmp_path):
    records = [{"id": 1, "secret": "value"}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "secret.stg"
    out = tmp_path / "out.json"
    os.environ["STANG_TEST_PASSPHRASE"] = "pw"
    try:
        assert main(["encode", str(src), str(stg), "--encrypt",
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        assert main(["decode", str(stg), str(out),
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        assert json.loads(out.read_text()) == records
    finally:
        del os.environ["STANG_TEST_PASSPHRASE"]


def test_wrong_passphrase_fails(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "secret.stg"
    os.environ["STANG_TEST_PASSPHRASE"] = "right"
    os.environ["STANG_TEST_WRONG"] = "wrong"
    try:
        assert main(["encode", str(src), str(stg), "--encrypt",
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        assert main(["decode", str(stg), str(tmp_path / "out.json"),
                     "--passphrase-env", "STANG_TEST_WRONG"]) == 1
    finally:
        del os.environ["STANG_TEST_PASSPHRASE"]
        del os.environ["STANG_TEST_WRONG"]


def test_dump_formats(tmp_path, capsys):
    records = [{"id": 1, "name": "Genz"}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    assert main(["encode", str(src), str(stg)]) == 0
    for fmt in ["block", "json", "ndjson", "csv", "tsv", "markdown", "stats", "raw"]:
        assert main(["dump", str(stg), "--format", fmt]) == 0
        capsys.readouterr()
    assert main(["dump", str(stg), "--format", "md"]) == 0


def test_inspect_plain_and_json(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    assert main(["encode", str(src), str(stg)]) == 0
    assert main(["inspect", str(stg)]) == 0
    out = capsys.readouterr().out
    assert "Format     : STG2" in out
    assert main(["inspect", str(stg), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == 2
    assert payload["record_count"] == 1


def test_inspect_encrypted_without_credentials(tmp_path, capsys):
    records = [{"id": 1, "field": "hidden"}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "secret.stg"
    os.environ["STANG_TEST_PASSPHRASE"] = "pw"
    try:
        assert main(["encode", str(src), str(stg), "--encrypt",
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        capsys.readouterr()
        assert main(["inspect", str(stg)]) == 0
        out = capsys.readouterr().out
        assert "encrypted" in out
        assert "hidden" not in out
    finally:
        del os.environ["STANG_TEST_PASSPHRASE"]


def test_rotate_updates_state(tmp_path, capsys):
    records = [{"id": i} for i in range(10)]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    assert main(["encode", str(src), str(stg), "--blocks", "4", "--rotation", "0"]) == 0
    assert main(["rotate", str(stg), "+2"]) == 0
    capsys.readouterr()
    assert main(["inspect", str(stg), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["rotation_state"] == 2


def test_rotate_rejects_bad_offset(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    assert main(["encode", str(src), str(stg)]) == 0
    assert main(["rotate", str(stg), "two"]) == 1


def test_keygen_lengths(capsys):
    assert main(["keygen"]) == 0
    token = capsys.readouterr().out.strip()
    assert len(token) >= 40
    assert main(["keygen", "--bytes", "8"]) == 1  # too low
    assert main(["keygen", "--hex", "--bytes", "16"]) == 0
    assert len(capsys.readouterr().out.strip()) == 32


def test_encode_rejects_bad_blocks(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    assert main(["encode", str(src), str(tmp_path / "x.stg"), "--blocks", "0"]) == 1


def test_dump_markdown_and_md_alias(tmp_path, capsys):
    records = [{"id": 1, "name": "Genz"}]
    src = _write_json(tmp_path, records)
    stg = tmp_path / "data.stg"
    assert main(["encode", str(src), str(stg)]) == 0
    assert main(["dump", str(stg), "--format", "markdown"]) == 0
    assert "| id |" in capsys.readouterr().out


def test_encode_ndjson(tmp_path, capsys):
    nd = tmp_path / "input.ndjson"
    nd.write_text(
        '{"id": 1, "name": "a"}\n'
        '\n'
        '# comment line is ignored\n'
        '{"id": 2, "name": "b"}\n',
        encoding="utf-8",
    )
    stg = tmp_path / "out.stg"
    assert main(["encode", str(nd), str(stg), "--input-format", "ndjson"]) == 0
    capsys.readouterr()
    out = tmp_path / "out.json"
    assert main(["decode", str(stg), str(out)]) == 0
    assert json.loads(out.read_text()) == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]


def test_encode_ndjson_rejects_non_object_line(tmp_path, capsys):
    nd = tmp_path / "bad.ndjson"
    nd.write_text('{"id": 1}\n[1, 2]\n', encoding="utf-8")
    assert main(["encode", str(nd), str(tmp_path / "x.stg"), "--input-format", "ndjson"]) == 1
    assert "NDJSON line 2" in capsys.readouterr().err


def test_diff_identical_different_rotation(tmp_path, capsys):
    records = [{"id": i, "name": f"n{i}"} for i in range(6)]
    src = _write_json(tmp_path, records)
    a = tmp_path / "a.stg"
    b = tmp_path / "b.stg"
    assert main(["encode", str(src), str(a), "--rotation", "0"]) == 0
    assert main(["encode", str(src), str(b), "--rotation", "2"]) == 0
    assert main(["diff", str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "IDENTICAL" in out
    assert "rotation" in out  # informational note about the rotation difference


def test_diff_detects_record_change(tmp_path, capsys):
    src_a = _write_json(tmp_path, [{"id": 1}, {"id": 2}])
    src_b = tmp_path / "b.json"
    src_b.write_text(json.dumps([{"id": 1}, {"id": 3}]), encoding="utf-8")
    a = tmp_path / "a.stg"
    b = tmp_path / "b.stg"
    assert main(["encode", str(src_a), str(a)]) == 0
    assert main(["encode", str(src_b), str(b)]) == 0
    assert main(["diff", str(a), str(b)]) == 1
    out = capsys.readouterr().out
    assert "DIFFERENT" in out
    assert "1 only in A" in out and "1 only in B" in out


def test_diff_json_output(tmp_path, capsys):
    records = [{"id": 1}]
    src = _write_json(tmp_path, records)
    a = tmp_path / "a.stg"
    b = tmp_path / "b.stg"
    assert main(["encode", str(src), str(a)]) == 0
    assert main(["encode", str(src), str(b)]) == 0
    assert main(["diff", str(a), str(b), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["identical_records"] is True
    assert report["records_a"] == report["records_b"] == 1


def test_diff_encrypted_without_credentials(tmp_path, capsys):
    src = _write_json(tmp_path, [{"id": 1}])
    stg = tmp_path / "secret.stg"
    os.environ["STANG_TEST_PASSPHRASE"] = "pw"
    try:
        assert main(["encode", str(src), str(stg), "--encrypt",
                     "--passphrase-env", "STANG_TEST_PASSPHRASE"]) == 0
        capsys.readouterr()
        assert main(["diff", str(stg), str(stg)]) == 2
    finally:
        del os.environ["STANG_TEST_PASSPHRASE"]

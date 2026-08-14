"""Quick inline verification script for STANG.

Run with:

    python verify.py

This does not replace pytest; it performs a few core sanity checks.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from stang import decode_stg, encode_stg, load_stg, save_stg
from stang.container import STGContainer
from stang.rotation import RotationEngine


def assert_eq(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> int:
    # Rotation engine
    engine = RotationEngine([0, 1, 2, 3, 4])
    assert_eq(engine.rotate(2), 2, "rotate(+2)")
    assert_eq(engine.rotate(4), 1, "rotate(+4)")
    assert_eq(engine.rotate(-2), 4, "rotate(-2)")
    assert_eq(engine.rotate(100), 0, "rotate overflow")

    # Round-trip
    records = [
        {"id": 1, "name": "Genz", "value": "example", "active": True, "meta": {"score": 9.5}},
        {"id": 2, "name": "Ana", "value": None, "active": False, "tags": ["a", "b"]},
    ]
    container = encode_stg(records, block_count=3, rotation_state=1)
    decoded = decode_stg(container)
    assert_eq(decoded, records, "round-trip")

    # File round-trip
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "data.stg"
        save_stg(path, records, block_count=3, rotation_state=2)
        loaded = load_stg(path)
        assert_eq(loaded, records, "file round-trip")

        # Rotation update
        from stang.cli import main as cli_main

        assert cli_main(["rotate", str(path), "+1"]) == 0
        assert cli_main(["verify", str(path)]) == 0

    # Determinism
    data = json.dumps(records, sort_keys=True).encode()
    c1 = STGContainer.deserialize(encode_stg(records, block_count=4).serialize())
    c2 = STGContainer.deserialize(encode_stg(records, block_count=4).serialize())
    assert_eq(c1.serialize(), c2.serialize(), "deterministic")

    print("All inline verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

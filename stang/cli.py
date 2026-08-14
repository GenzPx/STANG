"""Command-line interface for STANG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from stang import __version__
from stang.container import STGContainer
from stang.decoder import decode_stg, decode_to_json, load_stg
from stang.encoder import encode_from_json, encode_stg, save_stg
from stang.rotation import RotationEngine


def _read_json(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def _write_json(path: str | Path, data: bytes) -> None:
    Path(path).write_bytes(data)


def cmd_init(args: argparse.Namespace) -> int:
    """Create an empty STG container."""
    save_stg(args.file, [])
    print(f"Initialized empty STG container: {args.file}")
    return 0


def cmd_encode(args: argparse.Namespace) -> int:
    """Encode JSON input to a .stg file."""
    data = _read_json(args.input)
    container = encode_from_json(data, block_count=args.blocks)
    if args.rotation is not None:
        container.rotation_state = args.rotation % container.block_count
    Path(args.output).write_bytes(container.serialize())
    print(f"Encoded {args.input} -> {args.output}")
    print(f"  blocks={container.block_count}, rotation={container.rotation_state}")
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    """Decode a .stg file to JSON."""
    container = STGContainer.deserialize(Path(args.input).read_bytes())
    output = decode_to_json(container)
    _write_json(args.output, output)
    print(f"Decoded {args.input} -> {args.output}")
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    """Dump a .stg file using a selected dumper plugin."""
    from stang.dumpers import DUMPERS

    container = STGContainer.deserialize(Path(args.input).read_bytes())
    dumper_class = DUMPERS.get(args.format, DUMPERS["default"])
    print(dumper_class().dump(container))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show metadata without full decode."""
    data = Path(args.input).read_bytes()
    container = STGContainer.deserialize(data)
    print(f"File       : {args.input}")
    print(f"Magic      : {container.magic.decode('ascii')}")
    print(f"Version    : {container.version}")
    print(f"Flags      : {container.flags}")
    print(f"Blocks     : {container.block_count}")
    print(f"Rotation   : {container.rotation_state}")
    print(f"Records    : {sum(len(block) for block in container.blocks)}")
    print(f"Schema     : {container.schema.fields}")
    print(f"Checksum   : VALID")
    return 0


def cmd_rotate(args: argparse.Namespace) -> int:
    """Rotate a container's logical state and rewrite the file."""
    path = Path(args.input)
    container = STGContainer.deserialize(path.read_bytes())
    engine = RotationEngine(list(range(container.block_count)), container.rotation_state)
    engine.rotate(int(args.offset))
    container.rotation_state = engine.current_index()
    path.write_bytes(container.serialize())
    print(f"Rotated {args.input} to state {container.rotation_state}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify container integrity."""
    try:
        STGContainer.deserialize(Path(args.input).read_bytes())
        print(f"{args.input}: VALID")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"{args.input}: INVALID - {exc}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Print STANG runtime status."""
    import platform

    print(f"STANG {__version__}")
    print(f"Python: {platform.python_version()}")
    print("Status: OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stang",
        description="STANG: a rotational data container. Not a database engine.",
    )
    parser.add_argument("--version", action="version", version=f"stang {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create an empty STG container")
    init.add_argument("file", help="Output .stg file")
    init.set_defaults(func=cmd_init)

    encode = sub.add_parser("encode", help="Encode JSON to .stg")
    encode.add_argument("input", help="Input JSON file")
    encode.add_argument("output", help="Output .stg file")
    encode.add_argument("--blocks", type=int, default=4, help="Number of blocks")
    encode.add_argument("--rotation", type=int, default=None, help="Initial rotation state")
    encode.set_defaults(func=cmd_encode)

    decode = sub.add_parser("decode", help="Decode .stg to JSON")
    decode.add_argument("input", help="Input .stg file")
    decode.add_argument("output", help="Output JSON file")
    decode.set_defaults(func=cmd_decode)

    dump = sub.add_parser("dump", help="Dump .stg contents")
    dump.add_argument("input", help="Input .stg file")
    dump.add_argument(
        "--format",
        choices=["block", "json", "csv", "raw"],
        default="block",
        help="Output format",
    )
    dump.set_defaults(func=cmd_dump)

    inspect = sub.add_parser("inspect", help="Inspect .stg metadata")
    inspect.add_argument("input", help="Input .stg file")
    inspect.set_defaults(func=cmd_inspect)

    rotate = sub.add_parser("rotate", help="Rotate logical state of a .stg file")
    rotate.add_argument("input", help="Input .stg file")
    rotate.add_argument("offset", help="Rotation offset (integer)")
    rotate.set_defaults(func=cmd_rotate)

    verify = sub.add_parser("verify", help="Verify .stg integrity")
    verify.add_argument("input", help="Input .stg file")
    verify.set_defaults(func=cmd_verify)

    status = sub.add_parser("status", help="Show STANG status")
    status.set_defaults(func=cmd_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

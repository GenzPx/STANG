"""Command-line interface for STANG."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import secrets
import sys
from collections.abc import Sequence
from pathlib import Path

from stang import __version__
from stang.container import (
    FLAG_COMPRESSED,
    FLAG_ENCRYPTED,
    FLAG_HMAC,
    MAGIC_V1,
    MAGIC_V2,
    STGContainer,
)
from stang.decoder import decode_to_json
from stang.encoder import encode_from_json, save_stg
from stang.errors import AuthenticationError, ContainerError, IntegrityError, STANGError
from stang.rotation import RotationEngine

SUPPORTED_FORMATS = ("stg1", "stg2")


# --------------------------------------------------------------------- #
# Secret resolution helpers                                              #
# --------------------------------------------------------------------- #

def _read_secret_from_env(var: str) -> str:
    value = os.environ.get(var)
    if value is None:
        raise STANGError(f"Environment variable {var} is not set.")
    return value


def _read_secret_from_file(path: str, *, strip: bool) -> str | bytes:
    data = Path(path).read_bytes()
    if strip:
        return data.decode("utf-8").rstrip("\r\n")
    return data


def resolve_passphrase(args: argparse.Namespace, *, prompt: bool = True) -> str | bytes | None:
    """Resolve a passphrase from flags, the environment, or an interactive prompt."""
    if getattr(args, "passphrase_env", None):
        return _read_secret_from_env(args.passphrase_env)
    if getattr(args, "passphrase_file", None):
        result = _read_secret_from_file(args.passphrase_file, strip=True)
        assert isinstance(result, str)
        return result
    if prompt and sys.stdin.isatty():
        first = getpass.getpass("Passphrase: ")
        confirm = getpass.getpass("Confirm passphrase: ")
        if first != confirm:
            raise STANGError("Passphrases do not match.")
        return first
    return None


def resolve_passphrase_readonly(args: argparse.Namespace) -> str | bytes | None:
    """Resolve a passphrase for reading (single prompt, no confirmation)."""
    if getattr(args, "passphrase_env", None):
        return _read_secret_from_env(args.passphrase_env)
    if getattr(args, "passphrase_file", None):
        result = _read_secret_from_file(args.passphrase_file, strip=True)
        assert isinstance(result, str)
        return result
    if sys.stdin.isatty():
        return getpass.getpass("Passphrase: ")
    return None


def resolve_integrity_key(args: argparse.Namespace) -> bytes | str | None:
    """Resolve an integrity key from flags or the environment."""
    if getattr(args, "key_env", None):
        return _read_secret_from_env(args.key_env)
    if getattr(args, "key_file", None):
        result = _read_secret_from_file(args.key_file, strip=False)
        assert isinstance(result, bytes)
        return result
    return None


def add_secret_arguments(parser: argparse.ArgumentParser, *, write: bool) -> None:
    """Attach shared passphrase/key arguments to a subcommand parser."""
    group = parser.add_argument_group("credentials")
    group.add_argument("--passphrase-env", metavar="VAR",
                       help="Read the passphrase from environment variable VAR")
    group.add_argument("--passphrase-file", metavar="PATH",
                       help="Read the passphrase from PATH (trailing newline stripped)")
    if write:
        group.add_argument("--key-env", metavar="VAR",
                           help="Read the raw integrity key from environment variable VAR")
        group.add_argument("--key-file", metavar="PATH",
                           help="Read the raw integrity key bytes from PATH")


def add_format_argument(parser: argparse.ArgumentParser) -> None:
    """Attach the wire-format selector to a subcommand parser."""
    parser.add_argument("--format", dest="wire_format", choices=SUPPORTED_FORMATS,
                        default="stg2", help="Wire format to write (default: stg2)")


# --------------------------------------------------------------------- #
# Input/output helpers                                                   #
# --------------------------------------------------------------------- #

def _read_bytes(source: str) -> bytes:
    if source == "-":
        return sys.stdin.buffer.read()
    return Path(source).read_bytes()


def _write_bytes(target: str, data: bytes) -> None:
    if target == "-":
        sys.stdout.buffer.write(data)
        return
    Path(target).write_bytes(data)


def _load_container(
    path: str, args: argparse.Namespace
) -> STGContainer:
    """Deserialize a container, resolving credentials but not prompting blindly."""
    data = _read_bytes(path)
    needs_pass = _sniff_encrypted(data)
    needs_key = _sniff_hmac(data)
    passphrase = resolve_passphrase_readonly(args) if needs_pass else None
    integrity_key = resolve_integrity_key(args) if needs_key else None
    return STGContainer.deserialize(data, passphrase=passphrase, integrity_key=integrity_key)


def _sniff_encrypted(data: bytes) -> bool:
    return len(data) >= 6 and data[:4] == MAGIC_V2 and bool(data[5] & FLAG_ENCRYPTED)


def _sniff_hmac(data: bytes) -> bool:
    return len(data) >= 6 and data[:4] == MAGIC_V2 and bool(data[5] & FLAG_HMAC)


def _format_to_version(name: str) -> int:
    return 2 if name == "stg2" else 1


# --------------------------------------------------------------------- #
# Subcommands                                                            #
# --------------------------------------------------------------------- #

def cmd_init(args: argparse.Namespace) -> int:
    """Create an empty STG container."""
    passphrase = resolve_passphrase(args) if args.encrypt else None
    integrity_key = resolve_integrity_key(args) if args.hmac else None
    save_stg(
        args.file,
        [],
        block_count=args.blocks,
        rotation_state=args.rotation,
        passphrase=passphrase,
        integrity_key=integrity_key,
        compress=args.compress,
        format_version=_format_to_version(args.wire_format),
    )
    print(f"Initialized empty STG{_format_to_version(args.wire_format)} container: {args.file}")
    return 0


def cmd_encode(args: argparse.Namespace) -> int:
    """Encode JSON input to a .stg file."""
    data = _read_bytes(args.input)
    passphrase = resolve_passphrase(args) if args.encrypt else None
    integrity_key = resolve_integrity_key(args) if args.hmac else None
    container = encode_from_json(
        data,
        block_count=args.blocks,
        passphrase=passphrase,
        integrity_key=integrity_key,
        compress=args.compress,
        format_version=_format_to_version(args.wire_format),
    )
    if args.rotation is not None:
        container.rotation_state = args.rotation % container.block_count
    blob = container.serialize()
    _write_bytes(args.output, blob)
    print(f"Encoded {args.input} -> {args.output}", file=sys.stderr)
    summary = (
        f"  format=STG{container.format_version} blocks={container.block_count} "
        f"rotation={container.rotation_state} records={container.record_count} "
        f"size={len(blob)}B"
    )
    flags = []
    if container.is_compressed:
        raw = sum(len(json.dumps(list(b), ensure_ascii=False).encode()) for b in container.blocks)
        flags.append(f"zlib({raw}B->blocks)")
    if container.is_encrypted:
        flags.append("encrypted")
    if container.flags & FLAG_HMAC:
        flags.append("hmac")
    if flags:
        summary += " [" + ", ".join(flags) + "]"
    print(summary, file=sys.stderr)
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    """Decode a .stg file to JSON."""
    container = _load_container(args.input, args)
    output = decode_to_json(container)
    if args.pretty:
        parsed = json.loads(output)
        output = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    _write_bytes(args.output, output)
    print(f"Decoded {args.input} -> {args.output}", file=sys.stderr)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    """Dump a .stg file using a selected dumper plugin."""
    from stang.dumpers import DUMPERS

    container = _load_container(args.input, args)
    dumper_class = DUMPERS[args.format]
    print(dumper_class().dump(container))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show metadata without full decode."""
    data = _read_bytes(args.input)
    encrypted = _sniff_encrypted(data)
    keyed = _sniff_hmac(data)
    decrypt_failed = False
    passphrase = None
    integrity_key = None
    if encrypted:
        passphrase = resolve_passphrase_readonly(args)
    if keyed:
        integrity_key = resolve_integrity_key(args)
    container: STGContainer | None = None
    try:
        container = STGContainer.deserialize(
            data, passphrase=passphrase, integrity_key=integrity_key
        )
    except AuthenticationError:
        if passphrase is not None:
            raise
        decrypt_failed = True
    except IntegrityError:
        if integrity_key is not None:
            raise
        decrypt_failed = True

    if container is None:
        # Encrypted/keyed container viewed without credentials: header only.
        header = _header_summary(data)
        if args.json:
            print(json.dumps(header, indent=2))
        else:
            _print_header_summary(args.input, header)
            print("Schema     : (credentials required)")
            print("Checksum   : NOT EVALUATED (no credentials)")
        return 0

    if args.json:
        print(json.dumps(container.describe(), indent=2))
        return 0
    print(f"File       : {args.input}")
    print(f"Magic      : {container.magic.decode('ascii')}")
    print(f"Format     : STG{container.format_version}")
    print(f"Blocks     : {container.block_count}")
    print(f"Rotation   : {container.rotation_state}")
    print(f"Records    : {container.record_count}")
    flags = []
    if container.is_compressed:
        flags.append("compressed")
    if container.is_encrypted:
        flags.append("encrypted")
    if container.flags & FLAG_HMAC:
        flags.append("hmac")
    print(f"Flags      : {', '.join(flags) if flags else 'none'}")
    if decrypt_failed:
        print("Schema     : (credentials required)")
    else:
        print(f"Schema     : {container.schema.fields}")
    print("Checksum   : VALID")
    return 0


def _header_summary(data: bytes) -> dict[str, object]:
    import struct

    magic, version, flags, rotation_state, ext_len, block_count, _salt = struct.unpack(
        "!4sBBIIH16s", data[:32]
    )
    return {
        "magic": magic.decode("ascii", errors="replace"),
        "format": f"STG{version}",
        "version": version,
        "flags": flags,
        "compressed": bool(flags & FLAG_COMPRESSED),
        "encrypted": bool(flags & FLAG_ENCRYPTED),
        "hmac": bool(flags & FLAG_HMAC),
        "rotation_state": rotation_state,
        "block_count": block_count,
        "header_ext_len": ext_len,
        "size_bytes": len(data),
    }


def _print_header_summary(path: str, header: dict[str, object]) -> None:
    print(f"File       : {path}")
    print(f"Magic      : {header['magic']}")
    print(f"Format     : {header['format']}")
    print(f"Blocks     : {header['block_count']}")
    print(f"Rotation   : {header['rotation_state']}")
    flags = []
    if header["compressed"]:
        flags.append("compressed")
    if header["encrypted"]:
        flags.append("encrypted")
    if header["hmac"]:
        flags.append("hmac")
    print(f"Flags      : {', '.join(flags) if flags else 'none'}")
    print(f"Size       : {header['size_bytes']} bytes")


def cmd_rotate(args: argparse.Namespace) -> int:
    """Rotate a container's logical state and rewrite the file."""
    path = args.input
    data = _read_bytes(path)
    passphrase = resolve_passphrase_readonly(args) if _sniff_encrypted(data) else None
    integrity_key = resolve_integrity_key(args) if _sniff_hmac(data) else None
    container = STGContainer.deserialize(data, passphrase=passphrase, integrity_key=integrity_key)
    engine = RotationEngine(list(range(container.block_count)), container.rotation_state)
    try:
        offset = int(args.offset, 10)
    except ValueError:
        raise STANGError(f"Rotation offset must be an integer, got {args.offset!r}") from None
    engine.rotate(offset)
    container.rotation_state = engine.current_index()
    _write_bytes(path, container.serialize())
    print(f"Rotated {args.input} to state {container.rotation_state}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify container integrity."""
    data = _read_bytes(args.input)
    encrypted = _sniff_encrypted(data)
    keyed = _sniff_hmac(data)
    if encrypted and not _has_passphrase_source(args):
        print(f"{args.input}: ENCRYPTED (supply --passphrase-env/--passphrase-file to verify)")
        return 2
    if keyed and not getattr(args, "key_env", None) and not getattr(args, "key_file", None):
        print(f"{args.input}: KEYED (supply --key-env/--key-file to verify)")
        return 2
    passphrase = resolve_passphrase_readonly(args) if encrypted else None
    integrity_key = resolve_integrity_key(args) if keyed else None
    try:
        STGContainer.deserialize(data, passphrase=passphrase, integrity_key=integrity_key)
    except STANGError as exc:
        print(f"{args.input}: INVALID - {exc}")
        return 1
    print(f"{args.input}: VALID")
    return 0


def _has_passphrase_source(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "passphrase_env", None)
        or getattr(args, "passphrase_file", None)
        or sys.stdin.isatty()
    )


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert a .stg container between wire formats."""
    data = _read_bytes(args.input)
    target = _format_to_version(args.to)
    encrypted = _sniff_encrypted(data)
    keyed = _sniff_hmac(data)
    passphrase = resolve_passphrase_readonly(args) if encrypted else None
    integrity_key = resolve_integrity_key(args) if keyed else None
    container = STGContainer.deserialize(data, passphrase=passphrase, integrity_key=integrity_key)

    if target == 1:
        if container.is_encrypted or container.flags & FLAG_HMAC or container.is_compressed:
            raise STANGError(
                "STG1 cannot represent compression, encryption or HMAC. "
                "Convert to stg2 instead, or strip those options first."
            )
        container.format_version = 1
    else:
        container.format_version = 2
    _write_bytes(args.output, container.serialize())
    print(f"Converted {args.input} -> {args.output} (STG{container.format_version})")
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    """Generate a cryptographically random passphrase."""
    if args.bytes < 16:
        raise STANGError("--bytes must be at least 16")
    token = secrets.token_urlsafe(args.bytes)
    if args.hex:
        token = secrets.token_hex(args.bytes)
    print(token)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print STANG runtime status."""
    print(f"STANG {__version__}")
    print(f"Python            : {platform.python_version()} ({platform.python_implementation()})")
    print(f"Platform          : {platform.system()} {platform.release()}")
    print("Crypto            : pbkdf2-sha256 (100k iters) + HMAC-SHA256 counter mode")
    print(f"Formats           : {MAGIC_V2.decode()} (current), "
          f"{MAGIC_V1.decode()} (legacy, read/write)")
    print("Status            : OK")
    return 0


# --------------------------------------------------------------------- #
# Parser                                                                 #
# --------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the stang CLI."""
    parser = argparse.ArgumentParser(
        prog="stang",
        description="STANG: a rotational data container. Not a database engine.",
    )
    parser.add_argument("--version", action="version", version=f"stang {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create an empty STG container")
    init.add_argument("file", help="Output .stg file ('-' for stdout)")
    init.add_argument("--blocks", type=int, default=4, help="Number of blocks (default: 4)")
    init.add_argument("--rotation", type=int, default=0, help="Initial rotation state")
    init.add_argument("--compress", action="store_true", help="zlib-compress block payloads")
    init.add_argument("--encrypt", action="store_true",
                    help="Encrypt blocks (prompts for passphrase)")
    init.add_argument("--hmac", action="store_true",
                    help="HMAC-SHA256 integrity instead of plain SHA-256")
    add_secret_arguments(init, write=True)
    add_format_argument(init)
    init.set_defaults(func=cmd_init)

    encode = sub.add_parser("encode", help="Encode JSON to .stg")
    encode.add_argument("input", help="Input JSON file ('-' for stdin)")
    encode.add_argument("output", help="Output .stg file ('-' for stdout)")
    encode.add_argument("--blocks", type=int, default=4, help="Number of blocks (default: 4)")
    encode.add_argument("--rotation", type=int, default=None, help="Initial rotation state")
    encode.add_argument("--compress", action="store_true", help="zlib-compress block payloads")
    encode.add_argument("--encrypt", action="store_true",
                      help="Encrypt blocks (prompts for passphrase)")
    encode.add_argument("--hmac", action="store_true",
                      help="HMAC-SHA256 integrity instead of plain SHA-256")
    add_secret_arguments(encode, write=True)
    add_format_argument(encode)
    encode.set_defaults(func=cmd_encode)

    decode = sub.add_parser("decode", help="Decode .stg to JSON")
    decode.add_argument("input", help="Input .stg file ('-' for stdin)")
    decode.add_argument("output", help="Output JSON file ('-' for stdout)")
    decode.add_argument("--pretty", action="store_true",
                       help="Pretty-print the JSON output")
    add_secret_arguments(decode, write=True)
    decode.set_defaults(func=cmd_decode)

    from stang.dumpers import DUMPERS

    dump = sub.add_parser("dump", help="Dump .stg contents in various formats")
    dump.add_argument("input", help="Input .stg file ('-' for stdin)")
    dump.add_argument("--format", choices=sorted(k for k in DUMPERS if k != "default"),
                      default="block", help="Output format (default: block)")
    add_secret_arguments(dump, write=True)
    dump.set_defaults(func=cmd_dump)

    inspect = sub.add_parser("inspect", help="Inspect .stg metadata")
    inspect.add_argument("input", help="Input .stg file ('-' for stdin)")
    inspect.add_argument("--json", action="store_true",
                       help="Emit machine-readable JSON")
    add_secret_arguments(inspect, write=True)
    inspect.set_defaults(func=cmd_inspect)

    rotate = sub.add_parser("rotate", help="Rotate logical state of a .stg file")
    rotate.add_argument("input", help="Input .stg file")
    rotate.add_argument("offset", help="Relative rotation offset (integer, may be negative)")
    add_secret_arguments(rotate, write=True)
    rotate.set_defaults(func=cmd_rotate)

    verify = sub.add_parser("verify", help="Verify .stg integrity")
    verify.add_argument("input", help="Input .stg file")
    add_secret_arguments(verify, write=True)
    verify.set_defaults(func=cmd_verify)

    convert = sub.add_parser("convert", help="Convert between STG wire formats")
    convert.add_argument("input", help="Input .stg file")
    convert.add_argument("output", help="Output .stg file")
    convert.add_argument("--to", choices=SUPPORTED_FORMATS, required=True, help="Target format")
    add_secret_arguments(convert, write=True)
    convert.set_defaults(func=cmd_convert)

    keygen = sub.add_parser("keygen", help="Generate a random passphrase")
    keygen.add_argument("--bytes", type=int, default=32,
                      help="Token entropy in bytes (default: 32)")
    keygen.add_argument("--hex", action="store_true", help="Emit hex instead of base64url")
    keygen.set_defaults(func=cmd_keygen)

    status = sub.add_parser("status", help="Show STANG status")
    status.set_defaults(func=cmd_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``stang`` console script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except (STANGError, ContainerError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return int(result)


if __name__ == "__main__":
    sys.exit(main())

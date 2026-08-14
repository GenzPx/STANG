"""STANG: A Rotational Data Container.

STANG is a custom, versioned, self-describing file container format with a
built-in rotational access model. It is *not* a database engine, SQL database,
or replacement for SQLite/PostgreSQL. It stores structured data blocks and
accesses them via logical rotation state rather than linear cursors.

Public API surface for programmatic use.
"""

from stang.checksum import compute_checksum, verify_checksum
from stang.container import STGContainer
from stang.decoder import decode_stg, load_stg
from stang.encoder import encode_stg, save_stg
from stang.nodes import Node
from stang.rotation import RotationEngine
from stang.schema import Schema

__version__ = "1.0.0"

__all__ = [
    "STGContainer",
    "Schema",
    "RotationEngine",
    "Node",
    "encode_stg",
    "save_stg",
    "decode_stg",
    "load_stg",
    "compute_checksum",
    "verify_checksum",
]

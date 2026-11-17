"""STANG: A Rotational Data Container.

STANG is a custom, versioned, self-describing file container format with a
built-in rotational access model. It is *not* a database engine, SQL database,
or replacement for SQLite/PostgreSQL. It stores structured data blocks and
accesses them via logical rotation state rather than linear cursors.

Public API surface for programmatic use.
"""

from stang.checksum import compute_checksum, verify_checksum
from stang.container import STGContainer
from stang.decoder import decode_stg, decode_to_json, load_stg
from stang.encoder import encode_from_json, encode_stg, save_stg
from stang.errors import (
    AuthenticationError,
    ChecksumError,
    ContainerError,
    EncryptionError,
    IntegrityError,
    STANGError,
)
from stang.nodes import Node, NodeError, Pipeline, PipelineError
from stang.rotation import RotationEngine
from stang.schema import Schema, SchemaError

__version__ = "2.1.0"

__all__ = [
    "AuthenticationError",
    "ChecksumError",
    "ContainerError",
    "EncryptionError",
    "IntegrityError",
    "Node",
    "NodeError",
    "Pipeline",
    "PipelineError",
    "RotationEngine",
    "STANGError",
    "STGContainer",
    "Schema",
    "SchemaError",
    "compute_checksum",
    "decode_stg",
    "decode_to_json",
    "encode_from_json",
    "encode_stg",
    "load_stg",
    "save_stg",
    "verify_checksum",
]

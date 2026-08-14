"""Tests for integrity checking and error handling."""

import pytest

from stang.container import STGContainer, ContainerError
from stang.encoder import encode_stg


def test_checksum_corruption():
    container = encode_stg([{"id": 1}])
    data = bytearray(container.serialize())
    data[-1] ^= 0xFF
    with pytest.raises(ContainerError, match="Checksum mismatch"):
        STGContainer.deserialize(bytes(data))


def test_invalid_magic():
    container = encode_stg([{"id": 1}])
    data = bytearray(container.serialize())
    data[0] = ord("X")
    with pytest.raises(ContainerError, match="Invalid magic"):
        STGContainer.deserialize(bytes(data))


def test_unsupported_version():
    container = encode_stg([{"id": 1}])
    data = bytearray(container.serialize())
    data[4] = 99
    with pytest.raises(ContainerError, match="Unsupported STG version"):
        STGContainer.deserialize(bytes(data))


def test_truncated_file():
    container = encode_stg([{"id": 1}])
    data = container.serialize()[:10]
    with pytest.raises(ContainerError):
        STGContainer.deserialize(data)

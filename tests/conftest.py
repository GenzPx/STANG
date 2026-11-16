"""Shared fixtures for the STANG test-suite."""

from __future__ import annotations

import pytest


@pytest.fixture()
def sample_records() -> list[dict]:
    return [
        {"id": 1, "name": "Genz", "value": "example", "active": True, "meta": {"score": 9.5}},
        {"id": 2, "name": "Ana", "value": None, "active": False, "tags": ["a", "b"]},
        {"id": 3, "name": "Budi", "value": "sample", "active": True},
    ]


@pytest.fixture()
def golden_passphrase() -> str:
    return "secret-stang-key"

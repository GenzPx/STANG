"""Tests for the rotational engine."""

import pytest

from stang.rotation import RotationEngine


def test_initial_state():
    engine = RotationEngine([0, 1, 2, 3, 4])
    assert engine.current_index() == 0
    assert engine.current_position() == 0


def test_positive_rotation():
    engine = RotationEngine([0, 1, 2, 3, 4])
    assert engine.rotate(2) == 2
    assert engine.current_position() == 2


def test_negative_rotation():
    engine = RotationEngine([0, 1, 2, 3, 4])
    assert engine.rotate(-1) == 4
    assert engine.current_position() == 4


def test_overflow_rotation():
    engine = RotationEngine([0, 1, 2, 3, 4])
    assert engine.rotate(7) == 2
    assert engine.rotate(-12) == 0


def test_logical_not_physical():
    positions = ["a", "b", "c"]
    engine = RotationEngine(positions)
    engine.rotate(1)
    assert list(engine.positions()) == ["a", "b", "c"]
    assert engine.current_position() == "b"


def test_reset_and_normalize():
    engine = RotationEngine([0, 1, 2, 3])
    engine.rotate(5)
    assert engine.current_index() == 1
    assert engine.normalize(-1) == 3
    assert engine.reset() == 0


def test_empty_positions_rejected():
    with pytest.raises(ValueError):
        RotationEngine([])

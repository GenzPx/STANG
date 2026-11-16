"""Rotational access engine.

STANG does not walk through data linearly. It turns.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

T = TypeVar("T")


class RotationEngine(Generic[T]):
    """Logical rotation engine over a fixed collection of positions.

    Rotations are circular and do not mutate the underlying collection.
    Only the logical state changes.
    """

    def __init__(self, positions: Sequence[T], initial_position: int = 0) -> None:
        """Initialize the engine over a non-empty sequence of positions."""
        if not positions:
            raise ValueError("RotationEngine requires at least one position.")
        if not isinstance(initial_position, int) or isinstance(initial_position, bool):
            raise TypeError("initial_position must be an integer")
        self._positions: tuple[T, ...] = tuple(positions)
        self._count = len(self._positions)
        self._state = self._normalize(initial_position)

    @property
    def count(self) -> int:
        """Number of rotational positions."""
        return self._count

    def _normalize(self, offset: int) -> int:
        """Map any integer offset onto ``[0, count)`` using modular arithmetic."""
        return offset % self._count

    def rotate(self, offset: int) -> int:
        """Rotate the logical state by ``offset`` positions and return the new index."""
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise TypeError("rotation offset must be an integer")
        self._state = self._normalize(self._state + offset)
        return self._state

    def rotate_to(self, position_index: int) -> int:
        """Set the logical state directly to a normalized position index."""
        if not isinstance(position_index, int) or isinstance(position_index, bool):
            raise TypeError("position_index must be an integer")
        self._state = self._normalize(position_index)
        return self._state

    def current_index(self) -> int:
        """Return the current logical index into ``positions``."""
        return self._state

    def current_position(self) -> T:
        """Return the current position value."""
        return self._positions[self._state]

    def rotated_positions(self) -> tuple[T, ...]:
        """Return all positions ordered starting from the active state."""
        return self._positions[self._state :] + self._positions[: self._state]

    def normalize(self, offset: int) -> int:
        """Return the normalized index for ``offset`` without changing state."""
        return self._normalize(offset)

    def reset(self) -> int:
        """Reset the engine to position ``0``."""
        self._state = 0
        return self._state

    def positions(self) -> tuple[T, ...]:
        """Return the immutable sequence of positions."""
        return self._positions

    def __repr__(self) -> str:
        """Return developer-readable state summary."""
        return (
            f"{self.__class__.__name__}("
            f"count={self._count}, state={self._state}, "
            f"current={self.current_position()!r})"
        )

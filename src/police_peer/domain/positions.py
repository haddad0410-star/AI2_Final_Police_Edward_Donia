"""Canonical coordinate system for the whole domain layer.

Coordinate semantics (fixed, not configurable at this layer):
- Position stores (row, col) as zero-based integers.
- Origin (0, 0) is the TOP-LEFT cell, matching game.json's
  axis_origin_corner="top-left" / axis_start_index=0.
- row increases moving DOWN the board (toward "south"); col increases moving
  RIGHT (toward "east"). This is the one canonical representation used
  everywhere in this package -- never row/col-swapped, never x/y-swapped.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True, order=True)
class Position:
    """A zero-based (row, col) board coordinate. Immutable and hashable."""

    row: int
    col: int

    def is_within(self, grid_size: int) -> bool:
        return 0 <= self.row < grid_size and 0 <= self.col < grid_size

    def translated(self, d_row: int, d_col: int) -> Position:
        return Position(self.row + d_row, self.col + d_col)


class Direction(StrEnum):
    """The only five legal move directions (Appendix F: 4-orthogonal + STAY)."""

    N = "N"
    S = "S"
    E = "E"
    W = "W"
    STAY = "STAY"

    @property
    def delta(self) -> tuple[int, int]:
        """(d_row, d_col) for this direction, per this module's coordinate docstring."""
        return _DELTAS[self]


_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.N: (-1, 0),
    Direction.S: (1, 0),
    Direction.E: (0, 1),
    Direction.W: (0, -1),
    Direction.STAY: (0, 0),
}


def apply_direction(position: Position, direction: Direction) -> Position:
    """Return the cell reached by moving one step from `position` in `direction`."""
    d_row, d_col = direction.delta
    return position.translated(d_row, d_col)

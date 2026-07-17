"""The Board: grid geometry plus the (initially empty, then growing) set of
permanent barriers for one sub-game."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.positions import Direction, Position, apply_direction

ORTHOGONAL_DIRECTIONS: tuple[Direction, ...] = (
    Direction.N,
    Direction.S,
    Direction.E,
    Direction.W,
)


@dataclass(frozen=True, slots=True)
class Board:
    """Immutable board state: size + barriers. A new barrier means a new Board."""

    grid_size: int
    barriers: frozenset[Position] = frozenset()

    def is_in_bounds(self, position: Position) -> bool:
        return position.is_within(self.grid_size)

    def is_barrier(self, position: Position) -> bool:
        return position in self.barriers

    def with_barrier(self, cell: Position) -> Board:
        return Board(grid_size=self.grid_size, barriers=self.barriers | {cell})

    def adjacent_cells(self, position: Position) -> tuple[Position, ...]:
        """The (up to 4) orthogonally-adjacent cells, in-bounds only -- used
        both for barrier-placement legality and for the belief transition
        model's neighbor function."""
        return tuple(
            cell
            for d in ORTHOGONAL_DIRECTIONS
            if self.is_in_bounds(cell := apply_direction(position, d))
        )

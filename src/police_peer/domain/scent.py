"""Scent (pheromone) emission and decay -- book Ch.4.3, visually verified p.28.

Update formula for one full turn:
    tau_ij(t+1) = max(0, (1 - rho) * tau_ij(t) + delta_tau_ij)

`rho` is the shared config's pheromone_decay (constant 0.10). `delta_tau_ij` is
the fixed 5x5 emission matrix below, centered on the emitter's current
position and clipped -- never wrapped -- at the board edges.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.positions import Position

#: Exact 5x5 emission matrix (Appendix F Table 16 / Fig.4, visually verified).
#: Row/col offsets 0..4; center (index 2, 2) carries the peak intensity 0.9.
EMISSION_MATRIX: tuple[tuple[float, ...], ...] = (
    (0.04, 0.14, 0.20, 0.14, 0.04),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.20, 0.62, 0.90, 0.62, 0.20),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.04, 0.14, 0.20, 0.14, 0.04),
)
EMISSION_RADIUS = len(EMISSION_MATRIX) // 2  # 2, for a 5x5 window


@dataclass(frozen=True, slots=True)
class ScentField:
    """An immutable grid_size x grid_size scent grid; never mutated in place."""

    grid_size: int
    grid: tuple[tuple[float, ...], ...]

    def value_at(self, position: Position) -> float:
        return self.grid[position.row][position.col]


def empty_scent_field(grid_size: int) -> ScentField:
    """A fresh all-zero scent field for a board of the given size."""
    row = tuple(0.0 for _ in range(grid_size))
    return ScentField(grid_size=grid_size, grid=tuple(row for _ in range(grid_size)))


def _emission_delta(grid_size: int, source: Position) -> list[list[float]]:
    """The delta_tau_ij matrix for this turn: EMISSION_MATRIX centered on
    `source`, clipped (never wrapped) at the board edges."""
    delta = [[0.0] * grid_size for _ in range(grid_size)]
    for d_row in range(-EMISSION_RADIUS, EMISSION_RADIUS + 1):
        row = source.row + d_row
        if not (0 <= row < grid_size):
            continue
        for d_col in range(-EMISSION_RADIUS, EMISSION_RADIUS + 1):
            col = source.col + d_col
            if not (0 <= col < grid_size):
                continue
            delta[row][col] = EMISSION_MATRIX[d_row + EMISSION_RADIUS][d_col + EMISSION_RADIUS]
    return delta


def apply_turn(field: ScentField, source: Position, rho: float) -> ScentField:
    """One full turn's update: decay the existing field, then add fresh
    emission from `source` -- tau(t+1) = max(0, (1-rho)*tau(t) + delta_tau)."""
    delta = _emission_delta(field.grid_size, source)
    new_grid = tuple(
        tuple(max(0.0, (1 - rho) * field.grid[r][c] + delta[r][c]) for c in range(field.grid_size))
        for r in range(field.grid_size)
    )
    return ScentField(grid_size=field.grid_size, grid=new_grid)


@dataclass(frozen=True, slots=True)
class ScentHistory:
    """Append-only, immutable sequence of ScentField snapshots for replay/audit."""

    snapshots: tuple[ScentField, ...] = ()

    def appended(self, field: ScentField) -> ScentHistory:
        return ScentHistory(snapshots=self.snapshots + (field,))

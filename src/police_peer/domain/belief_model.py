"""The BeliefMap data type: a normalized probabilistic belief update, not
claimed to be formally Bayesian-optimal.

A BeliefMap represents THIS peer's own belief about where the OPPONENT most
likely is. It is built exclusively from public evidence (scent, hints, legal
transitions, barriers) -- no function in this module or belief_updates.py
ever accepts the opponent's true position as an input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from police_peer.domain.positions import Position


@dataclass(frozen=True, slots=True)
class BeliefMap:
    """An immutable grid_size x grid_size probability distribution."""

    grid_size: int
    grid: tuple[tuple[float, ...], ...]

    def probability_at(self, position: Position) -> float:
        return self.grid[position.row][position.col]

    def total_mass(self) -> float:
        return sum(sum(row) for row in self.grid)


def normalize(grid_size: int, raw_grid: list[list[float]]) -> BeliefMap:
    """Renormalize so probabilities sum to 1; falls back to a uniform
    distribution over the whole board if the total mass is ~0 (degenerate
    evidence must never crash or silently return an invalid distribution)."""
    total = sum(sum(row) for row in raw_grid)
    if total <= 1e-12:
        uniform = 1.0 / (grid_size * grid_size)
        grid = tuple(tuple(uniform for _ in range(grid_size)) for _ in range(grid_size))
        return BeliefMap(grid_size=grid_size, grid=grid)
    grid = tuple(tuple(v / total for v in row) for row in raw_grid)
    return BeliefMap(grid_size=grid_size, grid=grid)


def entropy(belief: BeliefMap) -> float:
    """Shannon entropy in bits; 0 = certain, higher = more uncertain."""
    total = 0.0
    for row in belief.grid:
        for p in row:
            if p > 0.0:
                total -= p * math.log2(p)
    return total


def most_likely(belief: BeliefMap) -> Position:
    best_pos = Position(0, 0)
    best_p = -1.0
    for r, row in enumerate(belief.grid):
        for c, p in enumerate(row):
            if p > best_p:
                best_p = p
                best_pos = Position(r, c)
    return best_pos


def top_k(belief: BeliefMap, k: int) -> list[tuple[Position, float]]:
    """The k highest-probability cells, descending, ties broken by row/col."""
    entries = [(Position(r, c), p) for r, row in enumerate(belief.grid) for c, p in enumerate(row)]
    entries.sort(key=lambda item: (-item[1], item[0].row, item[0].col))
    return entries[:k]


def expected_distance(belief: BeliefMap, from_position, distance_fn) -> float:
    """E[distance(from_position, opponent_cell)] under this belief."""
    total = 0.0
    for r, row in enumerate(belief.grid):
        for c, p in enumerate(row):
            if p > 0.0:
                total += p * distance_fn(from_position, Position(r, c))
    return total

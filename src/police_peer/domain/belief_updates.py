"""Belief-update primitives: prior, transition, scent evidence, hint evidence.

None of these take the opponent's true position as an argument -- structurally
impossible to leak it here (see tests/unit/test_belief.py, which introspects
every function's signature to confirm this).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from police_peer.domain.belief_model import BeliefMap, normalize
from police_peer.domain.positions import Position
from police_peer.domain.scent import ScentField


def uniform_prior(grid_size: int, barriers: Iterable[Position] = ()) -> BeliefMap:
    """Uniform belief over every non-barrier cell; barrier cells get zero."""
    barrier_set = set(barriers)
    raw = [
        [0.0 if Position(r, c) in barrier_set else 1.0 for c in range(grid_size)]
        for r in range(grid_size)
    ]
    return normalize(grid_size, raw)


def apply_barrier_mask(belief: BeliefMap, barriers: Iterable[Position]) -> BeliefMap:
    """Zero out any cell a barrier occupies (physically impossible), renormalize."""
    barrier_set = set(barriers)
    raw = [
        [0.0 if Position(r, c) in barrier_set else p for c, p in enumerate(row)]
        for r, row in enumerate(belief.grid)
    ]
    return normalize(belief.grid_size, raw)


def apply_transition(
    belief: BeliefMap, neighbors_fn: Callable[[Position], Iterable[Position]]
) -> BeliefMap:
    """Predict step: spread each cell's mass uniformly over its legal
    successor cells (a simple diffusion transition model), before any new
    evidence is folded in this turn."""
    grid_size = belief.grid_size
    raw = [[0.0] * grid_size for _ in range(grid_size)]
    for r, row in enumerate(belief.grid):
        for c, p in enumerate(row):
            if p <= 0.0:
                continue
            successors = list(neighbors_fn(Position(r, c)))
            if not successors:
                raw[r][c] += p
                continue
            share = p / len(successors)
            for successor in successors:
                raw[successor.row][successor.col] += share
    return normalize(grid_size, raw)


def apply_scent_likelihood(belief: BeliefMap, scent: ScentField, trust: float = 1.0) -> BeliefMap:
    """Update step: cells with stronger opponent scent become more likely.
    All-zero scent evidence is a safe no-op (uniform likelihood everywhere)."""
    raw = [
        [p * (1.0 + trust * scent.grid[r][c]) for c, p in enumerate(row)]
        for r, row in enumerate(belief.grid)
    ]
    return normalize(belief.grid_size, raw)


def apply_hint_likelihood(
    belief: BeliefMap, hint_region: Iterable[Position] | None, base_trust: float = 0.5
) -> BeliefMap:
    """Update step: boost cells the hint points at, with trust CALIBRATED by
    how much the region already agrees with existing (physical/scent)
    evidence -- a hint that contradicts strong prior evidence is down-weighted
    rather than allowed to corrupt the belief with a physically-implausible
    claim."""
    if hint_region is None:
        return belief
    region_set = set(hint_region)
    if not region_set:
        return belief
    grid_size = belief.grid_size
    prior_region_mass = sum(belief.grid[p.row][p.col] for p in region_set)
    agreement = prior_region_mass * grid_size * grid_size / len(region_set)
    effective_trust = base_trust * min(1.0, agreement)
    raw = [
        [
            p * (1.0 + effective_trust) if Position(r, c) in region_set else p
            for c, p in enumerate(row)
        ]
        for r, row in enumerate(belief.grid)
    ]
    return normalize(grid_size, raw)

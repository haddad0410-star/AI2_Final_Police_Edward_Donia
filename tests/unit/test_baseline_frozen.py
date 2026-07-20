"""Batch 3, Task 2: regression guard -- BaselinePoliceBrain's identity and
decision behavior must never be altered by advanced-strategy work in this
batch. Compares against the frozen baseline_snapshot.json produced from
real session recovery step C evidence."""

from __future__ import annotations

import random

from police_peer.domain.belief_model import normalize
from police_peer.domain.board import Board
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.positions import Direction, Position
from police_peer.domain.rules import legal_move_directions
from police_peer.strategy import BaselinePoliceBrain, DecisionRequest

GRID = 7
FROZEN_MODULE = "police_peer.strategy.baseline_police_brain"
FROZEN_CLASS = "BaselinePoliceBrain"


def test_baseline_module_path_unchanged() -> None:
    assert BaselinePoliceBrain.__module__ == FROZEN_MODULE
    assert BaselinePoliceBrain.__name__ == FROZEN_CLASS


def test_baseline_never_places_a_barrier() -> None:
    brain = BaselinePoliceBrain()
    rng = random.Random(1234)
    board = Board(grid_size=GRID)
    for _ in range(200):
        pos = Position(rng.randrange(GRID), rng.randrange(GRID))
        raw = [[0.01] * GRID for _ in range(GRID)]
        raw[rng.randrange(GRID)][rng.randrange(GRID)] = 100.0
        belief = normalize(GRID, raw)
        request = DecisionRequest(
            own_position=pos,
            legal_directions=legal_move_directions(pos, board),
            belief=belief,
            step=1,
            rng=random.Random(rng.randrange(1_000_000)),
            deadline=DeadlineTracker(30.0).start(),
        )
        assert brain.decide(request).barrier is None


def test_baseline_deterministic_decision_at_fixed_scenario() -> None:
    """A pinned (position, belief, seed) scenario's decision must remain
    byte-identical -- if this ever fails, BaselinePoliceBrain's algorithm
    changed, which this batch must never do."""
    brain = BaselinePoliceBrain()
    raw = [[0.01] * GRID for _ in range(GRID)]
    raw[0][6] = 100.0
    belief = normalize(GRID, raw)
    request = DecisionRequest(
        own_position=Position(0, 0),
        legal_directions=legal_move_directions(Position(0, 0), Board(grid_size=GRID)),
        belief=belief,
        step=1,
        rng=random.Random(42),
        deadline=DeadlineTracker(30.0).start(),
    )
    decision = brain.decide(request)
    assert decision.direction is Direction.E
    assert decision.barrier is None
    assert decision.honest_intent is True

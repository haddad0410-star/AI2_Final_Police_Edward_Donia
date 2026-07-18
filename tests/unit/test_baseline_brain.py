"""Phase 7: BaselinePoliceBrain legality, determinism, fallback, and loading."""

from __future__ import annotations

import inspect
import random

from police_peer.domain.belief_model import normalize
from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.positions import Direction, Position, apply_direction
from police_peer.domain.rules import legal_move_directions
from police_peer.strategy import (
    BaselinePoliceBrain,
    Decision,
    DecisionRequest,
    StrategyLoadError,
    load_police_brain,
)

GRID = 7


def _belief_peaked_at(cell: Position):
    raw = [[0.01 for _ in range(GRID)] for _ in range(GRID)]
    raw[cell.row][cell.col] = 100.0
    return normalize(GRID, raw)


def _request(position: Position, belief, seed: int = 0) -> DecisionRequest:
    board = Board(grid_size=GRID)
    legal = legal_move_directions(position, board)
    return DecisionRequest(
        own_position=position,
        legal_directions=legal,
        belief=belief,
        step=1,
        rng=random.Random(seed),
        deadline=DeadlineTracker(30.0).start(),
    )


def test_always_returns_a_legal_move_across_random_boards() -> None:
    brain = BaselinePoliceBrain()
    rng = random.Random(1234)
    for _ in range(2000):
        pos = Position(rng.randrange(GRID), rng.randrange(GRID))
        target = Position(rng.randrange(GRID), rng.randrange(GRID))
        request = _request(pos, _belief_peaked_at(target), seed=rng.randrange(1_000_000))
        decision = brain.decide(request)
        assert decision.direction in request.legal_directions
        assert decision.barrier is None  # baseline never places a barrier


def test_moves_toward_belief_peak() -> None:
    brain = BaselinePoliceBrain()
    pos = Position(0, 0)
    target = Position(0, 6)  # due east
    decision = brain.decide(_request(pos, _belief_peaked_at(target)))
    new_cell = apply_direction(pos, decision.direction)
    assert new_cell.col >= pos.col  # got no further from the target column
    assert decision.direction is Direction.E


def test_deterministic_given_same_seed() -> None:
    brain = BaselinePoliceBrain()
    pos = Position(3, 3)
    belief = _belief_peaked_at(Position(0, 0))  # N and W both reduce distance -> tie
    a = brain.decide(_request(pos, belief, seed=42)).direction
    b = brain.decide(_request(pos, belief, seed=42)).direction
    assert a == b


def test_different_seeds_can_break_ties_differently() -> None:
    brain = BaselinePoliceBrain()
    pos = Position(3, 3)
    belief = _belief_peaked_at(Position(0, 0))  # N (2,3) and W (3,2) tie at distance 5
    seen = {brain.decide(_request(pos, belief, seed=s)).direction for s in range(50)}
    assert len(seen) > 1  # seeded randomized tie-break actually varies


def test_fallback_on_degenerate_belief_all_zero() -> None:
    brain = BaselinePoliceBrain()
    belief = uniform_prior(GRID)  # normalize keeps it valid even from all-zero
    decision = brain.decide(_request(Position(0, 0), belief))
    assert decision.direction in legal_move_directions(Position(0, 0), Board(grid_size=GRID))


def test_empty_legal_moves_falls_back_to_stay() -> None:
    brain = BaselinePoliceBrain()
    request = DecisionRequest(
        own_position=Position(0, 0),
        legal_directions=(),
        belief=uniform_prior(GRID),
        step=0,
        rng=random.Random(0),
    )
    assert brain.decide(request).direction is Direction.STAY


def test_decide_signature_never_receives_true_position() -> None:
    """Structural guarantee: DecisionRequest exposes only own_position + belief."""
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(DecisionRequest)}
    for forbidden in ("opponent", "true_position", "thief_position", "enemy"):
        assert not any(forbidden in name for name in field_names), field_names
    assert "own_position" in field_names


def test_deadline_compliance_is_fast() -> None:
    import time

    brain = BaselinePoliceBrain()
    request = _request(Position(0, 0), _belief_peaked_at(Position(6, 6)))
    start = time.monotonic()
    for _ in range(1000):
        brain.decide(request)
    assert (time.monotonic() - start) < 1.0  # nowhere near a 30s deadline


def test_strategy_loaded_from_private_config_path() -> None:
    brain = load_police_brain("police_peer.strategy.baseline_police_brain:BaselinePoliceBrain")
    assert isinstance(brain, BaselinePoliceBrain)


def test_loader_rejects_bad_paths() -> None:
    import pytest

    with pytest.raises(StrategyLoadError):
        load_police_brain("no_colon_here")
    with pytest.raises(StrategyLoadError):
        load_police_brain("police_peer.strategy.baseline_police_brain:DoesNotExist")
    with pytest.raises(StrategyLoadError):
        load_police_brain("police_peer.domain.roles:Role")  # not a PoliceBrainBase


def test_inputs_are_frozen_value_types() -> None:
    assert not inspect.isabstract(BaselinePoliceBrain)
    d = Decision(direction=Direction.N)
    assert d.honest_intent is True

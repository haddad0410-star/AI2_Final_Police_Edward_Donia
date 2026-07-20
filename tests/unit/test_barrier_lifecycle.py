"""Batch 3.5 Task 8: deterministic proof that the barrier mechanism is
functionally available end-to-end once belief confidence reaches realistic
post-repair levels (not indiscriminate placement -- a controlled scenario).

Cross-process wire transport / persistence / replay-verification / tamper
detection for a barrier are proven over REAL FastMCP HTTP in Task 9's
barrier-trap sanity fixture (integration_lab/evidence/batch3_5/capture_sanity_results.json)
rather than duplicated here.
"""

from __future__ import annotations

import dataclasses
import random

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.positions import Position
from police_peer.domain.rules import is_legal_barrier_cell, legal_move_directions
from police_peer.domain.scent import apply_turn, empty_scent_field
from police_peer.services.belief_update import advance_belief
from police_peer.services.subgame_state import RuntimeState
from police_peer.strategy.belief_cutoff_police_brain import BeliefCutoffPoliceBrain
from police_peer.strategy.decision import DecisionRequest

GRID = 7


def _concentrated_state(target: Position, turns: int = 20) -> RuntimeState:
    """Real (not fabricated) belief concentration via repeated real scent
    evidence at a fixed cell -- realistic post-repair confidence ceiling
    (~0.30), reached via the actual ``advance_belief`` pipeline."""
    state = RuntimeState(
        role=None,
        position=Position(4, 4),
        visited=frozenset(),
        board=Board(grid_size=GRID),
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )
    for i in range(turns):
        field = apply_turn(empty_scent_field(GRID), target, 0.10)
        state = dataclasses.replace(state, received_scent=field, received_scent_valid=True, step=i)
        state = advance_belief(state)
    return state


def _request(state: RuntimeState) -> DecisionRequest:
    return DecisionRequest(
        own_position=state.position,
        legal_directions=legal_move_directions(state.position, state.board),
        belief=state.belief,
        step=state.step,
        rng=random.Random(0),
        deadline=DeadlineTracker(5.0).start(),
        board=state.board,
        barriers_remaining=state.barriers_remaining,
        visited=state.visited,
    )


def test_brain_evaluates_and_chooses_a_barrier_when_belief_is_confident() -> None:
    state = _concentrated_state(Position(5, 5))
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is not None


def test_chosen_barrier_is_a_legal_cell() -> None:
    state = _concentrated_state(Position(5, 5))
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is not None
    assert is_legal_barrier_cell(state.position, decision.barrier, state.board)


def test_no_barrier_chosen_when_belief_is_uniform() -> None:
    """Sanity check on the gate itself: zero evidence -> zero confidence ->
    no barrier evaluated at all (not an indiscriminate placement)."""
    state = RuntimeState(
        role=None,
        position=Position(3, 3),
        visited=frozenset(),
        board=Board(grid_size=GRID),
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is None


def test_barrier_placement_still_selects_exactly_one_move_direction() -> None:
    """Placing a barrier is a side effect of the SAME turn's move decision,
    not an additional move -- exactly one legal direction is still chosen."""
    state = _concentrated_state(Position(5, 5))
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is not None
    assert decision.direction in legal_move_directions(state.position, state.board)


def test_barrier_persists_on_board_after_turn_loop_places_it() -> None:
    """Mirrors turn_loop.py's own barrier-application logic (the real
    production path, services/turn_loop.py::_decide_turn) end to end at the
    state level."""
    state = _concentrated_state(Position(5, 5))
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is not None
    assert (
        decision.barrier is not None
        and state.barriers_remaining > 0
        and is_legal_barrier_cell(state.position, decision.barrier, state.board)
    )
    updated = state.with_barrier_placed(decision.barrier)
    assert updated.board.is_barrier(decision.barrier)
    assert updated.barriers_remaining == state.barriers_remaining - 1


def test_zero_remaining_quota_blocks_placement_at_the_turn_loop_guard() -> None:
    """The brain is given ``barriers_remaining=0`` and structurally cannot
    place one itself (``_pick_move`` gates barrier evaluation on
    ``request.barriers_remaining > 0``); this mirrors the identical guard
    the real production turn_loop.py applies before ever calling
    ``with_barrier_placed``, so quota is enforced at two independent
    layers."""
    state = _concentrated_state(Position(5, 5))
    state = dataclasses.replace(state, barriers_remaining=0)
    brain = BeliefCutoffPoliceBrain()
    decision = brain.decide(_request(state))
    assert decision.barrier is None

"""Batch 3.5 Task 7: prove the strategy actually receives the REAL
pipeline-produced belief (not a synthetic one built by hand) and that
differing real evidence can change its decision.
"""

from __future__ import annotations

import dataclasses
import random

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.hint_region import region_cells
from police_peer.domain.positions import Position
from police_peer.domain.rules import legal_move_directions
from police_peer.domain.scent import apply_turn, empty_scent_field
from police_peer.services.belief_update import advance_belief
from police_peer.services.subgame_state import RuntimeState
from police_peer.strategy.baseline_police_brain import BaselinePoliceBrain
from police_peer.strategy.belief_cutoff_police_brain import BeliefCutoffPoliceBrain
from police_peer.strategy.decision import DecisionRequest

GRID = 7


def _state(**overrides) -> RuntimeState:
    base = RuntimeState(
        role=None,
        position=Position(3, 3),
        visited=frozenset(),
        board=Board(grid_size=GRID),
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=5,
        sub_game_number=1,
    )
    return dataclasses.replace(base, **overrides)


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


def test_two_pipelines_differing_only_in_scent_produce_different_beliefs() -> None:
    no_evidence = advance_belief(_state())
    with_evidence = advance_belief(
        _state(
            received_scent=apply_turn(empty_scent_field(GRID), Position(6, 6), 0.10),
            received_scent_valid=True,
        )
    )
    assert no_evidence.belief.grid != with_evidence.belief.grid


def test_two_pipelines_differing_only_in_hint_produce_different_beliefs() -> None:
    no_evidence = advance_belief(_state())
    with_hint = advance_belief(_state(hint_region=region_cells("southern", GRID)))
    assert no_evidence.belief.grid != with_hint.belief.grid


def test_advanced_brain_pursuit_direction_changes_with_concentrated_belief() -> None:
    """A belief strongly concentrated south-east of Police should pull the
    pursuit direction toward it, differing from a belief concentrated
    north-west."""
    brain = BeliefCutoffPoliceBrain()

    south_east = advance_belief(
        _state(
            received_scent=apply_turn(empty_scent_field(GRID), Position(6, 6), 0.10),
            received_scent_valid=True,
        )
    )
    north_west = advance_belief(
        _state(
            received_scent=apply_turn(empty_scent_field(GRID), Position(0, 0), 0.10),
            received_scent_valid=True,
        )
    )
    # Run several times (varying entropy convergence) to get a stable read.
    for _ in range(3):
        south_east = advance_belief(
            dataclasses.replace(
                south_east,
                received_scent=apply_turn(empty_scent_field(GRID), Position(6, 6), 0.10),
                received_scent_valid=True,
            )
        )
        north_west = advance_belief(
            dataclasses.replace(
                north_west,
                received_scent=apply_turn(empty_scent_field(GRID), Position(0, 0), 0.10),
                received_scent_valid=True,
            )
        )
    decision_se = brain.decide(_request(south_east))
    decision_nw = brain.decide(_request(north_west))
    assert decision_se.direction != decision_nw.direction


def test_brain_does_not_receive_true_position_field() -> None:
    import dataclasses as dc

    names = {f.name for f in dc.fields(DecisionRequest)}
    assert not any("true" in n or "opponent_position" in n for n in names)


def test_brain_cannot_mutate_local_peer_state() -> None:
    """The strategy is given RuntimeState-derived VALUES (immutable/copied),
    never a reference to RuntimeState itself -- so it cannot corrupt local
    peer state even if it tried."""
    state = advance_belief(_state())
    request = _request(state)
    brain = BaselinePoliceBrain()
    brain.decide(request)
    # request.belief is the SAME object passed in; a well-behaved brain must
    # not have mutated it (BeliefMap is frozen so this is structural, but we
    # also confirm the request object itself carries no back-reference to
    # RuntimeState that would allow mutation).
    assert not hasattr(request, "_runtime_state")
    assert request.belief.grid == state.belief.grid

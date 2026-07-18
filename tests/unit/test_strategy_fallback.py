"""Coverage for the PoliceBrainBase safety fallbacks and reveal ingestion."""

from __future__ import annotations

import random

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.positions import Direction, Position
from police_peer.domain.rules import legal_move_directions
from police_peer.services.capture_resolution import ingest_opponent_reveal
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentReveal
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.decision import Decision, DecisionRequest

GRID = 7


class _RaisingBrain(PoliceBrainBase):
    def _pick_move(self, request: DecisionRequest) -> Decision:
        raise RuntimeError("boom")


class _IllegalBrain(PoliceBrainBase):
    def _pick_move(self, request: DecisionRequest) -> Decision:
        return Decision(direction=Direction.N)  # will be illegal from a corner top row


def _request(position: Position) -> DecisionRequest:
    return DecisionRequest(
        own_position=position,
        legal_directions=legal_move_directions(position, Board(grid_size=GRID)),
        belief=uniform_prior(GRID),
        step=0,
        rng=random.Random(0),
    )


def test_exception_falls_back_to_first_legal() -> None:
    decision = _RaisingBrain().decide(_request(Position(3, 3)))
    assert decision.direction in legal_move_directions(Position(3, 3), Board(grid_size=GRID))


def test_illegal_move_is_replaced_by_fallback() -> None:
    # From (0,0), N leaves the board, so it is not in legal_directions -> fallback.
    decision = _IllegalBrain().decide(_request(Position(0, 0)))
    assert decision.direction in legal_move_directions(Position(0, 0), Board(grid_size=GRID))
    assert decision.direction is not Direction.N


def _state() -> RuntimeState:
    from police_peer.domain.scent import empty_scent_field

    return RuntimeState(
        role=None,  # unused in ingestion
        position=Position(0, 0),
        visited=frozenset(),
        board=Board(grid_size=GRID),
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )


def test_ingest_updates_scent_and_barrier() -> None:
    grid = tuple(tuple(0.5 for _ in range(GRID)) for _ in range(GRID))
    reveal = OpponentReveal(move="N", hint="", scent_grid=grid, barrier=(2, 2))
    updated = ingest_opponent_reveal(_state(), reveal)
    assert updated.received_scent.value_at(Position(0, 0)) == 0.5
    assert updated.board.is_barrier(Position(2, 2))


def test_ingest_ignores_out_of_bounds_barrier_and_bad_scent() -> None:
    reveal = OpponentReveal(move="S", hint="", scent_grid=(), barrier=(99, 99))
    updated = ingest_opponent_reveal(_state(), reveal)
    assert not updated.board.is_barrier(Position(99, 99))

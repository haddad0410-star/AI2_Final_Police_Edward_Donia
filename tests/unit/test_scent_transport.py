"""Batch 3.5 Task 4: scent transport repair coverage.

Proves the raw scent grid actually crosses serialization/commitment/reveal,
that malformed/missing scent takes the explicit missing-evidence path, and
that belief updates correctly from real received scent.
"""

from __future__ import annotations

import json

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.crypto import SealedTurnPayload, compute_commit_hash
from police_peer.domain.crypto.sealing import digest_scent_grid
from police_peer.domain.positions import Position
from police_peer.domain.scent import apply_turn, empty_scent_field
from police_peer.domain.scent_validation import validate_scent_grid
from police_peer.services.belief_update import advance_belief
from police_peer.services.capture_resolution import ingest_opponent_reveal
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentReveal

GRID = 7


def _payload(scent_grid) -> SealedTurnPayload:
    return SealedTurnPayload(
        step=0,
        role="police",
        sub_game_number=1,
        position=(0, 0),
        move="N",
        barrier_placed=None,
        intent="truth",
        hint="the northern avenues look fine",
        scent_digest=digest_scent_grid(scent_grid),
        scent_grid=scent_grid,
        capture_claim=(0, 0),
        claim_response=None,
        win_claim=False,
        config_sha256="c" * 64,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce="a" * 64,
    )


def test_nonzero_scent_crosses_real_serialization() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(3, 3), 0.10)
    payload = _payload(field.grid)
    wire = json.loads(json.dumps(payload.public_reveal_dict()))
    assert wire["scent_grid"][3][3] == field.grid[3][3] > 0.0


def test_dimensions_survive_round_trip() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(0, 0), 0.10)
    wire = json.loads(json.dumps(_payload(field.grid).public_reveal_dict()))
    assert len(wire["scent_grid"]) == GRID
    assert all(len(row) == GRID for row in wire["scent_grid"])


def test_values_survive_canonical_serialization() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(2, 4), 0.10)
    wire = json.loads(json.dumps(_payload(field.grid).public_reveal_dict()))
    for r in range(GRID):
        for c in range(GRID):
            assert wire["scent_grid"][r][c] == field.grid[r][c]


def test_recipient_receives_correct_public_field() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(1, 1), 0.10)
    reveal = _payload(field.grid).public_reveal_dict()
    assert "scent_grid" in reveal
    assert "scent_digest" in reveal


def test_commitment_covers_scent() -> None:
    field_a = apply_turn(empty_scent_field(GRID), Position(1, 1), 0.10)
    field_b = apply_turn(empty_scent_field(GRID), Position(5, 5), 0.10)
    hash_a = compute_commit_hash(_payload(field_a.grid))
    hash_b = compute_commit_hash(_payload(field_b.grid))
    assert hash_a != hash_b


def test_tampered_scent_fails_commitment_check() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(1, 1), 0.10)
    payload = _payload(field.grid)
    committed = compute_commit_hash(payload)
    tampered_grid = tuple(
        tuple(v + 1.0 if (r, c) == (0, 0) else v for c, v in enumerate(row))
        for r, row in enumerate(field.grid)
    )
    tampered = _payload(tampered_grid)
    assert compute_commit_hash(tampered) != committed


def test_missing_scent_is_explicit_missing_evidence() -> None:
    state = _state()
    reveal = OpponentReveal(move="N", hint="", scent_grid=None, barrier=None)
    updated = ingest_opponent_reveal(state, reveal)
    assert updated.received_scent_valid is False


def test_malformed_scent_rejected_wrong_dims() -> None:
    state = _state()
    reveal = OpponentReveal(move="N", hint="", scent_grid=((0.1, 0.2),), barrier=None)
    updated = ingest_opponent_reveal(state, reveal)
    assert updated.received_scent_valid is False


def test_malformed_scent_rejected_negative_value() -> None:
    grid = tuple(tuple(-0.1 for _ in range(GRID)) for _ in range(GRID))
    assert validate_scent_grid(grid, GRID) == "negative"


def test_malformed_scent_rejected_non_finite() -> None:
    grid = [[float("nan")] * GRID for _ in range(GRID)]
    assert validate_scent_grid(grid, GRID) == "non_finite"


def test_malformed_scent_rejected_exceeds_legal_maximum() -> None:
    grid = [[100.0] * GRID for _ in range(GRID)]
    assert validate_scent_grid(grid, GRID) == "exceeds_legal_maximum"


def test_valid_scent_accepted() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(3, 3), 0.10)
    assert validate_scent_grid(field.grid, GRID) is None


def test_old_scent_not_reused_as_new_evidence() -> None:
    state = _state()
    field = apply_turn(empty_scent_field(GRID), Position(3, 3), 0.10)
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint="", scent_grid=field.grid, barrier=None)
    )
    assert state.received_scent_valid is True
    # Next turn: opponent's reveal carries no scent field at all (missing).
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint="", scent_grid=None, barrier=None)
    )
    assert state.received_scent_valid is False  # not silently re-validated as "still fresh"


def test_edge_emission_clips_not_wraps() -> None:
    field = apply_turn(empty_scent_field(GRID), Position(0, 0), 0.10)
    assert field.grid[GRID - 1][GRID - 1] == 0.0  # never wraps to the far corner
    assert field.grid[0][0] == 0.9


def test_receiving_valid_scent_changes_belief() -> None:
    state = _state()
    field = apply_turn(empty_scent_field(GRID), Position(5, 5), 0.10)
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint="", scent_grid=field.grid, barrier=None)
    )
    before = state.belief
    after = advance_belief(state)
    assert after.belief.grid[5][5] != before.grid[5][5]


def test_belief_remains_normalized_after_scent_update() -> None:
    state = _state()
    field = apply_turn(empty_scent_field(GRID), Position(2, 2), 0.10)
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint="", scent_grid=field.grid, barrier=None)
    )
    after = advance_belief(state)
    total = sum(sum(row) for row in after.belief.grid)
    assert abs(total - 1.0) < 1e-9


def test_impossible_cells_remain_zero_after_scent_update() -> None:
    board = Board(grid_size=GRID).with_barrier(Position(3, 3))
    state = _state(board=board)
    field = apply_turn(empty_scent_field(GRID), Position(3, 3), 0.10)
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint="", scent_grid=field.grid, barrier=None)
    )
    after = advance_belief(state)
    assert after.belief.grid[3][3] == 0.0


def test_no_exact_position_field_on_reveal() -> None:
    """``position`` in a reveal is always THIS peer's own, already-committed
    cell (Batch 4B: a real top-level field, part of the ``commitment/1``
    canonical schema) -- not a leak, since ``capture_claim`` already
    reveals the identical coordinate every turn by design (the public "am
    I on you?" claim). The real invariant is that no OPPONENT-position
    field ever exists."""
    field = apply_turn(empty_scent_field(GRID), Position(1, 1), 0.10)
    reveal = _payload(field.grid).public_reveal_dict()
    assert reveal["position"] == [0, 0]  # this peer's own cell (fixed in _payload), expected
    assert "true_position" not in reveal
    assert "opponent_true_position" not in reveal
    assert "opponent_position" not in reveal


def test_no_true_position_inference_shortcut_in_opponent_reveal() -> None:
    import dataclasses

    fields = {f.name for f in dataclasses.fields(OpponentReveal)}
    assert not any("true" in name for name in fields)


def _state(board: Board | None = None) -> RuntimeState:
    grid_board = board if board is not None else Board(grid_size=GRID)
    return RuntimeState(
        role=None,
        position=Position(0, 0),
        visited=frozenset(),
        board=grid_board,
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )

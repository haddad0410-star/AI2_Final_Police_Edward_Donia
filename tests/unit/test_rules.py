"""Tests for board movement, barrier, and capture rules."""

from __future__ import annotations

import pytest

from police_peer.domain.actions import BarrierAction, MoveAction
from police_peer.domain.board import Board
from police_peer.domain.positions import Direction, Position
from police_peer.domain.roles import Role
from police_peer.domain.rules import (
    IllegalActionError,
    apply_move,
    is_barrier_on_thief_capture,
    is_legal_barrier_cell,
    is_ordinary_capture,
    legal_move_directions,
    place_barrier,
)

GRID = 7


def test_every_orthogonal_direction_is_legal_in_open_space() -> None:
    board = Board(grid_size=GRID)
    legal = legal_move_directions(Position(3, 3), board)
    assert set(legal) == {Direction.N, Direction.S, Direction.E, Direction.W, Direction.STAY}


def test_stay_is_always_legal_even_when_fully_surrounded() -> None:
    center = Position(3, 3)
    board = Board(grid_size=GRID)
    for d in (Direction.N, Direction.S, Direction.E, Direction.W):
        from police_peer.domain.positions import apply_direction

        board = board.with_barrier(apply_direction(center, d))
    legal = legal_move_directions(center, board)
    assert legal == (Direction.STAY,)


def test_diagonal_is_not_a_valid_direction_at_all() -> None:
    valid_values = {d.value for d in Direction}
    assert valid_values == {"N", "S", "E", "W", "STAY"}


def test_boundary_rejection() -> None:
    board = Board(grid_size=GRID)
    legal = legal_move_directions(Position(0, 0), board)
    assert Direction.N not in legal
    assert Direction.W not in legal
    assert Direction.S in legal
    assert Direction.E in legal


def test_barrier_collision_rejects_movement_into_it() -> None:
    board = Board(grid_size=GRID).with_barrier(Position(3, 4))
    legal = legal_move_directions(Position(3, 3), board)
    assert Direction.E not in legal


def test_apply_move_raises_on_illegal_direction() -> None:
    board = Board(grid_size=GRID)
    with pytest.raises(IllegalActionError):
        apply_move(Position(0, 0), MoveAction(Direction.N), board)


def test_apply_move_returns_new_position() -> None:
    board = Board(grid_size=GRID)
    new_pos = apply_move(Position(3, 3), MoveAction(Direction.E), board)
    assert new_pos == Position(3, 4)


def test_barrier_legal_on_own_cell_and_adjacent_cells() -> None:
    board = Board(grid_size=GRID)
    actor = Position(3, 3)
    assert is_legal_barrier_cell(actor, actor, board) is True
    assert is_legal_barrier_cell(actor, Position(3, 4), board) is True
    assert is_legal_barrier_cell(actor, Position(2, 2), board) is False  # not adjacent


def test_barrier_illegal_out_of_bounds_or_on_existing_barrier() -> None:
    board = Board(grid_size=GRID).with_barrier(Position(0, 1))
    assert is_legal_barrier_cell(Position(0, 0), Position(-1, 0), board) is False
    assert is_legal_barrier_cell(Position(0, 0), Position(0, 1), board) is False


def test_place_barrier_is_police_only() -> None:
    board = Board(grid_size=GRID)
    with pytest.raises(IllegalActionError, match="police"):
        place_barrier(Role.THIEF, Position(3, 3), BarrierAction(Position(3, 3)), board, 0, 14)


def test_place_barrier_enforces_quota() -> None:
    board = Board(grid_size=GRID)
    with pytest.raises(IllegalActionError, match="quota"):
        place_barrier(Role.POLICE, Position(3, 3), BarrierAction(Position(3, 3)), board, 14, 14)


def test_place_barrier_success_adds_permanent_barrier() -> None:
    board = Board(grid_size=GRID)
    new_board = place_barrier(
        Role.POLICE, Position(3, 3), BarrierAction(Position(3, 4)), board, 0, 14
    )
    assert new_board.is_barrier(Position(3, 4)) is True
    assert board.is_barrier(Position(3, 4)) is False  # original board untouched


def test_ordinary_capture_same_cell() -> None:
    assert is_ordinary_capture(Position(2, 2), Position(2, 2)) is True
    assert is_ordinary_capture(Position(2, 2), Position(2, 3)) is False


def test_barrier_on_thief_cell_is_a_capture() -> None:
    assert is_barrier_on_thief_capture(Position(5, 5), Position(5, 5)) is True
    assert is_barrier_on_thief_capture(Position(5, 5), Position(5, 6)) is False


def test_deterministic_replay_of_state_transitions() -> None:
    """Applying the same sequence of moves twice from the same start yields
    the same final position -- no hidden randomness in movement rules."""
    board = Board(grid_size=GRID)
    moves = [Direction.E, Direction.E, Direction.S, Direction.STAY, Direction.N]

    def replay() -> Position:
        pos = Position(3, 3)
        for d in moves:
            pos = apply_move(pos, MoveAction(d), board)
        return pos

    assert replay() == replay()

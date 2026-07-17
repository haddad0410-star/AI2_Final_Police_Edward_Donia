"""Movement, barrier, and capture rules -- visually verified against the book
(Ch.3.4 "Barrier Law" box, printed p.21; Appendix E rules 46-48), not HW6.

Interpretation note (see docs/adr/ADR-0011-trapped-thief-interpretation.md):
STAY is always legal (Appendix F Table 15: constant move set including STAY),
so a thief can never have zero legal actions. We therefore do NOT implement a
separate "trapped = automatic technical loss" rule beyond the two book-
confirmed early-end conditions: ordinary same-cell capture, and a barrier
placed on the thief's current cell (Appendix E rule 46).
"""

from __future__ import annotations

from police_peer.domain.actions import BarrierAction, MoveAction
from police_peer.domain.board import Board
from police_peer.domain.positions import Direction, Position, apply_direction
from police_peer.domain.roles import Role


class IllegalActionError(Exception):
    """Raised when a move or barrier placement violates the rules."""


def legal_move_directions(position: Position, board: Board) -> tuple[Direction, ...]:
    """STAY is always legal. An orthogonal direction is legal iff the
    destination is in-bounds and not a barrier."""
    legal = [Direction.STAY]
    for d in (Direction.N, Direction.S, Direction.E, Direction.W):
        dest = apply_direction(position, d)
        if board.is_in_bounds(dest) and not board.is_barrier(dest):
            legal.append(d)
    return tuple(legal)


def apply_move(position: Position, action: MoveAction, board: Board) -> Position:
    """Return the new position after `action`, raising if illegal."""
    if action.direction not in legal_move_directions(position, board):
        raise IllegalActionError(f"{action.direction} is not legal from {position}")
    return apply_direction(position, action.direction)


def is_legal_barrier_cell(actor_position: Position, cell: Position, board: Board) -> bool:
    """A barrier may be placed on the police's own current cell or one of its
    (up to 4) orthogonally-adjacent cells -- never an arbitrary board cell."""
    if not board.is_in_bounds(cell):
        return False
    if board.is_barrier(cell):
        return False
    return cell == actor_position or cell in board.adjacent_cells(actor_position)


def place_barrier(
    role: Role,
    actor_position: Position,
    action: BarrierAction,
    board: Board,
    barriers_placed_count: int,
    max_barriers: int,
) -> Board:
    """Return a new Board with the barrier added, enforcing every rule:
    police-only, legal adjacency, and the shared-config barrier quota."""
    if role is not Role.POLICE:
        raise IllegalActionError("only the police may place a barrier")
    if barriers_placed_count >= max_barriers:
        raise IllegalActionError(f"barrier quota exhausted ({max_barriers})")
    if not is_legal_barrier_cell(actor_position, action.cell, board):
        raise IllegalActionError(f"illegal barrier cell {action.cell} from {actor_position}")
    return board.with_barrier(action.cell)


def is_ordinary_capture(thief_position: Position, police_position: Position) -> bool:
    """Same-cell capture: the two peers' true positions coincide."""
    return thief_position == police_position


def is_barrier_on_thief_capture(barrier_cell: Position, thief_position: Position) -> bool:
    """Appendix E rule 46: a barrier placed on the thief's current cell is
    itself a capture, distinct from an ordinary same-cell capture."""
    return barrier_cell == thief_position

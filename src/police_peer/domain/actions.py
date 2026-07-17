"""The three action shapes a peer may submit on its turn.

Exactly one of these is chosen per turn: a move (including STAY, modeled as a
MoveAction with direction=STAY), or -- police only, instead of moving -- a
barrier placement.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.positions import Direction, Position


@dataclass(frozen=True, slots=True)
class MoveAction:
    """Move one cell in `direction` (Direction.STAY means: do not move)."""

    direction: Direction


@dataclass(frozen=True, slots=True)
class StayAction:
    """Explicit "do nothing this turn" action, distinct from MoveAction(STAY)
    for callers that want a dedicated type rather than checking `.direction`."""


@dataclass(frozen=True, slots=True)
class BarrierAction:
    """Police-only: place a permanent barrier at `cell` instead of moving.

    `cell` must be the police's current position or one of its four
    orthogonally-adjacent cells (enforced by domain.rules, not here).
    """

    cell: Position


#: The type of any single turn's chosen action.
Action = MoveAction | StayAction | BarrierAction

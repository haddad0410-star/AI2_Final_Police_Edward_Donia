"""RuntimeState: the peer's OWN sub-game truth plus legally-public info.

There is deliberately no field holding the opponent's true position (or any
equivalent) here; a grep/introspection test enforces that. The only
Position-typed own field is ``position``; ``board.barriers`` and
``received_scent`` are public information.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from police_peer.domain.belief_model import BeliefMap
from police_peer.domain.board import Board
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import ScentField


@dataclass(frozen=True, slots=True)
class RuntimeState:
    """This peer's own immutable sub-game state (updated functionally)."""

    role: Role
    position: Position
    visited: frozenset[Position]
    board: Board
    barriers_remaining: int
    belief: BeliefMap
    own_scent: ScentField
    received_scent: ScentField
    step: int
    sub_game_number: int

    def moved_to(self, cell: Position) -> RuntimeState:
        """Return a copy after moving to ``cell`` (records it as visited)."""
        return replace(self, position=cell, visited=self.visited | {cell})

    def with_belief(self, belief: BeliefMap) -> RuntimeState:
        return replace(self, belief=belief)

    def with_own_scent(self, scent: ScentField) -> RuntimeState:
        return replace(self, own_scent=scent)

    def with_received_scent(self, scent: ScentField) -> RuntimeState:
        return replace(self, received_scent=scent)

    def with_board(self, board: Board) -> RuntimeState:
        return replace(self, board=board)

    def advanced_step(self) -> RuntimeState:
        return replace(self, step=self.step + 1)

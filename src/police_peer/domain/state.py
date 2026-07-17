"""LocalPeerState: this peer's own truth plus legally-received public info.

Structurally, this dataclass has no way to hold the opponent's true position:
its only Position-typed field is `position` (this peer's own), and
`barriers_placed` holds publicly-declared barrier cells (legal for either side
to know). See tests/unit/test_local_peer_state.py for a signature/field
introspection test enforcing this, not just a comment promise.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from police_peer.domain.belief_model import BeliefMap
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import ScentField, ScentHistory


@dataclass(frozen=True, slots=True)
class LocalPeerState:
    """One peer's complete local truth at a point in time."""

    role: Role
    position: Position
    visited: frozenset[Position]
    barriers_placed: tuple[Position, ...]
    barriers_remaining: int
    step: int
    sub_game_number: int
    belief: BeliefMap
    own_scent_field: ScentField
    opponent_scent_history: ScentHistory = field(default_factory=ScentHistory)

    def with_step(self, step: int) -> LocalPeerState:
        """Return a copy advanced to a new step (immutability-preserving update)."""
        return LocalPeerState(
            role=self.role,
            position=self.position,
            visited=self.visited,
            barriers_placed=self.barriers_placed,
            barriers_remaining=self.barriers_remaining,
            step=step,
            sub_game_number=self.sub_game_number,
            belief=self.belief,
            own_scent_field=self.own_scent_field,
            opponent_scent_history=self.opponent_scent_history,
        )

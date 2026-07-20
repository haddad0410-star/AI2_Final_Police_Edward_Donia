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

#: Neutral starting trust for hint evidence (Batch 3.5 Task 5); the verdict
#: (intent) is sealed, so trust is earned/lost only via consistency history.
NEUTRAL_HINT_TRUST = 0.5


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
    #: True only when this turn's ``received_scent`` is real, validated
    #: evidence -- False (the default) means "no evidence this turn", an
    #: explicit missing-evidence state distinct from a genuine all-zero
    #: reading (Batch 3.5 Task 4, requirement 11).
    received_scent_valid: bool = False
    #: The region a just-received hint decodes to, or None if no hint
    #: evidence is available this turn (Batch 3.5 Task 5).
    hint_region: frozenset[Position] | None = None
    #: Bounded [0,1] consistency-based trust in hint evidence, carried across
    #: turns within one sub-game; never derived from the sealed intent field.
    hint_trust: float = NEUTRAL_HINT_TRUST

    def moved_to(self, cell: Position) -> RuntimeState:
        """Return a copy after moving to ``cell`` (records it as visited)."""
        return replace(self, position=cell, visited=self.visited | {cell})

    def with_belief(self, belief: BeliefMap) -> RuntimeState:
        return replace(self, belief=belief)

    def with_own_scent(self, scent: ScentField) -> RuntimeState:
        return replace(self, own_scent=scent)

    def with_received_scent(self, scent: ScentField, *, valid: bool = True) -> RuntimeState:
        return replace(self, received_scent=scent, received_scent_valid=valid)

    def with_no_scent_evidence(self) -> RuntimeState:
        """Explicit missing-evidence path (Batch 3.5 Task 4, requirement 11):
        this turn produced no usable scent evidence -- distinct from a
        genuine all-zero reading, which would still set ``valid=True``."""
        return replace(self, received_scent_valid=False)

    def with_hint_region(self, region: frozenset[Position] | None) -> RuntimeState:
        return replace(self, hint_region=region)

    def with_hint_trust(self, trust: float) -> RuntimeState:
        return replace(self, hint_trust=trust)

    def with_board(self, board: Board) -> RuntimeState:
        return replace(self, board=board)

    def with_barrier_placed(self, cell: Position) -> RuntimeState:
        """Apply OUR OWN newly-placed barrier to the local board and
        decrement the remaining quota. Legality (adjacency, quota, in
        bounds) must already have been checked by the caller."""
        return replace(
            self,
            board=self.board.with_barrier(cell),
            barriers_remaining=self.barriers_remaining - 1,
        )

    def advanced_step(self) -> RuntimeState:
        return replace(self, step=self.step + 1)

"""Per-turn belief maintenance for the sub-game runtime (reuses Batch 1).

Runs the Batch 1 belief primitives in order: diffuse (transition), fold in the
opponent's public scent, then mask out barrier cells. Never consumes the
opponent's true position -- only public evidence held in ``RuntimeState``.
"""

from __future__ import annotations

from police_peer.domain.belief_updates import (
    apply_barrier_mask,
    apply_scent_likelihood,
    apply_transition,
)
from police_peer.domain.positions import Position
from police_peer.services.subgame_state import RuntimeState


def advance_belief(state: RuntimeState) -> RuntimeState:
    """Return ``state`` with its belief advanced one turn from public evidence."""
    board = state.board

    def neighbors(cell: Position):
        return (*board.adjacent_cells(cell), cell)  # includes STAY

    belief = apply_transition(state.belief, neighbors)
    belief = apply_scent_likelihood(belief, state.received_scent)
    belief = apply_barrier_mask(belief, board.barriers)
    return state.with_belief(belief)

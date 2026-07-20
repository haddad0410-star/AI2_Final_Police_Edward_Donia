"""Per-turn belief maintenance for the sub-game runtime (reuses Batch 1).

Frozen turn-level update order (Batch 3.5 Task 6, see
``docs/BELIEF_MODEL.md``): prior belief -> legal transition prediction ->
barrier/impossible-cell masking -> newest scent likelihood -> newest hint
likelihood -> normalization. Never consumes the opponent's true position --
only public evidence held in ``RuntimeState``.
"""

from __future__ import annotations

from police_peer.domain.belief_model import entropy
from police_peer.domain.belief_updates import (
    apply_barrier_mask,
    apply_hint_likelihood,
    apply_scent_likelihood,
    apply_transition,
)
from police_peer.domain.positions import Position
from police_peer.services.subgame_state import RuntimeState

#: Bounded trust adjustment rates: a hint that sharpens belief (entropy
#: drops) earns trust slowly; one that contradicts it (entropy rises) loses
#: trust faster -- consistency history stands in for the sealed intent
#: verdict, which must never be used for this (Batch 3.5 Task 5).
_TRUST_GAIN = 0.08
_TRUST_LOSS = 0.12
_TRUST_FLOOR = 0.05
_TRUST_CEILING = 0.95


def _update_hint_trust(current_trust: float, entropy_before: float, entropy_after: float) -> float:
    if entropy_after < entropy_before - 1e-9:
        return min(_TRUST_CEILING, current_trust + _TRUST_GAIN * (1.0 - current_trust))
    if entropy_after > entropy_before + 1e-9:
        return max(_TRUST_FLOOR, current_trust - _TRUST_LOSS * current_trust)
    return current_trust


def advance_belief(state: RuntimeState) -> RuntimeState:
    """Return ``state`` with its belief advanced one turn from public evidence."""
    board = state.board

    def neighbors(cell: Position):
        return (*board.adjacent_cells(cell), cell)  # includes STAY

    belief = apply_transition(state.belief, neighbors)
    belief = apply_barrier_mask(belief, board.barriers)
    if state.received_scent_valid:
        belief = apply_scent_likelihood(belief, state.received_scent)
    new_trust = state.hint_trust
    if state.hint_region is not None:
        entropy_before_hint = entropy(belief)
        belief = apply_hint_likelihood(belief, state.hint_region, state.hint_trust)
        new_trust = _update_hint_trust(state.hint_trust, entropy_before_hint, entropy(belief))
    return state.with_belief(belief).with_hint_trust(new_trust)

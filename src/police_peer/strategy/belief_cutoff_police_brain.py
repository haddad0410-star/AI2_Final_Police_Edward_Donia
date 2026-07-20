"""BeliefCutoffPoliceBrain: original advanced Police strategy (Batch 3,
Task 3). See docs/STRATEGY.md for the full documented design and utility
formula.

Uses the complete belief distribution (not just its argmax), a bounded
belief-transition lookahead, entropy-driven pursuit/exploration switching,
and explicit barrier-placement evaluation over every legal candidate cell.
Never accesses -- and structurally cannot access, per ``DecisionRequest``'s
field set -- the opponent's true position.
"""

from __future__ import annotations

import math

from police_peer.domain.belief_model import BeliefMap, entropy, top_k
from police_peer.domain.positions import Position, apply_direction
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.belief_cutoff_config import DEFAULT_WEIGHTS, BeliefCutoffWeights
from police_peer.strategy.belief_cutoff_hint_trust import HintTrustTracker
from police_peer.strategy.belief_cutoff_utility import (
    barrier_utility,
    project_belief,
    score_move,
)
from police_peer.strategy.decision import Decision, DecisionRequest

_TOP_K = 3


class BeliefCutoffPoliceBrain(PoliceBrainBase):
    """Belief-state pursuit with bounded lookahead and barrier engineering."""

    def __init__(self, weights: BeliefCutoffWeights | None = None) -> None:
        self._weights = weights or DEFAULT_WEIGHTS
        self._hint_trust = HintTrustTracker()
        self._max_barriers: int | None = None

    def _pick_move(self, request: DecisionRequest) -> Decision:
        w = self._weights
        if self._max_barriers is None:
            self._max_barriers = request.barriers_remaining

        current_entropy = entropy(request.belief)
        trust = self._hint_trust.observe(current_entropy)
        exploring = current_entropy > self._hint_trust.scaled_explore_threshold(
            w.entropy_explore_threshold
        )

        board = request.board
        projected = (
            project_belief(request.belief, board, w.lookahead_depth)
            if board is not None
            else request.belief
        )
        cells = top_k(request.belief, _TOP_K)

        best_direction = request.legal_directions[0]
        best_score = float("-inf")
        best_destination = request.own_position
        for direction in request.legal_directions:
            destination = apply_direction(request.own_position, direction)
            s = score_move(
                origin=request.own_position,
                destination=destination,
                belief=request.belief,
                projected_belief=projected,
                visited=request.visited,
                top_k_cells=cells,
                exploring=exploring,
                weights=w,
            )
            if s > best_score:
                best_score, best_direction, best_destination = s, direction, destination

        barrier = None
        confident = _belief_confidence(request.belief, current_entropy) >= w.barrier_confidence_gate
        if board is not None and request.barriers_remaining > 0 and confident:
            barrier = self._best_barrier(request, board, best_destination, trust)

        return Decision(direction=best_direction, barrier=barrier, honest_intent=True)

    def _best_barrier(
        self, request: DecisionRequest, board, movement_destination: Position, trust: float
    ):
        """Evaluate every legal candidate cell (own cell + orthogonal
        neighbors, per Task 3E); never the cell this same turn's own move
        is about to occupy (would be self-contradictory), never below the
        configured utility floor -- a low-confidence belief (low trust)
        raises the effective floor, so barriers are reserved for when
        evidence has been reliable (Task 3E "dynamic reservation")."""
        w = self._weights
        candidates = [request.own_position, *board.adjacent_cells(request.own_position)]
        floor = w.barrier_utility_floor * (1.5 - trust)
        best_cell = None
        best_utility = floor
        for cell in candidates:
            if cell == movement_destination or board.is_barrier(cell):
                continue
            utility = barrier_utility(
                cell=cell,
                board=board,
                belief=request.belief,
                barriers_remaining=request.barriers_remaining,
                max_barriers=self._max_barriers or 1,
                weights=w,
            )
            if utility > best_utility:
                best_utility, best_cell = utility, cell
        return best_cell


def _belief_confidence(belief: BeliefMap, current_entropy: float) -> float:
    """Normalized inverse entropy in [0, 1]: 1.0 = certain (single-cell
    belief), 0.0 = maximally uncertain (uniform over the whole board).
    Feeds Task 3E's "use fewer barriers while belief confidence is poor" --
    a near-uniform belief's argmax is a tie-break artifact, not real
    signal, so barrier evaluation is skipped below the confidence gate."""
    max_entropy = math.log2(belief.grid_size * belief.grid_size)
    if max_entropy <= 0:
        return 1.0
    return max(0.0, 1.0 - current_entropy / max_entropy)

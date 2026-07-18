"""BaselinePoliceBrain: our own from-scratch, deliberately-simple police floor.

Design (strategy_proposals.md Section 1): move toward ``belief.most_likely()``
by greedy Manhattan-distance reduction; never place a barrier. Ties are broken
by the injected RNG, so behaviour is reproducible given a seed (deterministic
in test mode, seeded-random in league mode). This is NOT a copy of the
reference repository's heuristic.
"""

from __future__ import annotations

from police_peer.domain.belief_model import most_likely
from police_peer.domain.positions import Position, apply_direction
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.decision import Decision, DecisionRequest


def _manhattan(a: Position, b: Position) -> int:
    return abs(a.row - b.row) + abs(a.col - b.col)


class BaselinePoliceBrain(PoliceBrainBase):
    """Greedy pursuit of the single most-likely opponent cell; no barriers."""

    def _pick_move(self, request: DecisionRequest) -> Decision:
        """Pick the legal move that most reduces Manhattan distance to the belief peak.

        Never inspects a true opponent position -- only ``request.belief``. On a
        degenerate (all-zero) belief the normalized grid is uniform, so this
        still returns a legal move rather than failing.
        """
        target = most_likely(request.belief)
        scored: list[tuple[int, object]] = []
        for direction in request.legal_directions:
            cell = apply_direction(request.own_position, direction)
            scored.append((_manhattan(cell, target), direction))
        best_distance = min(distance for distance, _ in scored)
        tied = [direction for distance, direction in scored if distance == best_distance]
        chosen = request.rng.choice(tied) if len(tied) > 1 else tied[0]
        return Decision(direction=chosen, barrier=None, honest_intent=True)

"""Configurable utility weights for :class:`BeliefCutoffPoliceBrain`
(Batch 3, Task 3G). Weights are a plain, private, documented dataclass --
never hardcoded scattered through the decision logic, never part of the
signed shared ``game.json`` (Batch 3 rule 12).
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class BeliefCutoffWeights:
    """Utility-function component weights; see docs/STRATEGY.md for the
    full documented formula each one feeds into."""

    #: weight on expected-distance reduction toward the belief mass
    expected_distance: float = 1.0
    #: bonus for moving into one of the top-k believed-likely cells
    capture_opportunity: float = 2.0
    #: weight on projected post-lookahead expected distance (pursuit signal)
    lookahead_distance: float = 0.8
    #: penalty per prior visit to the candidate cell (loop avoidance)
    revisit_penalty: float = 0.15
    #: entropy (bits) above which frontier exploration is preferred over
    #: direct pursuit of the single believed-likely region
    entropy_explore_threshold: float = 3.0
    #: bonus for moving toward under-explored board regions while entropy
    #: is high
    frontier_bonus: float = 0.6
    #: barrier utility weight on reachable-area reduction
    barrier_area_reduction: float = 1.5
    #: barrier utility weight on proximity to the believed-likely region
    barrier_belief_proximity: float = 1.0
    #: barrier utility penalty for consuming part of a scarce remaining quota
    barrier_scarcity_penalty: float = 0.5
    #: minimum barrier utility required before a barrier is placed at all
    barrier_utility_floor: float = 0.75
    #: bounded lookahead depth (belief transition steps), 2-4 per Task 3D
    lookahead_depth: int = 2

    def with_overrides(self, **overrides: float) -> BeliefCutoffWeights:
        """Return a copy with the given fields overridden -- used by the
        tuning harness (Task 8) to try bounded candidate configurations
        without ever mutating a shared instance."""
        return replace(self, **overrides)


DEFAULT_WEIGHTS = BeliefCutoffWeights()


def weights_from_dict(data: dict) -> BeliefCutoffWeights:
    """Build weights from a private-config dict; unknown keys are rejected
    (a mistyped weight name must never be silently ignored)."""
    known = set(BeliefCutoffWeights.__dataclass_fields__)
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown BeliefCutoffWeights key(s): {sorted(unknown)}")
    return BeliefCutoffWeights(**data)

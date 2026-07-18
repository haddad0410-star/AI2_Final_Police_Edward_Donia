"""Strategy input/output value types (Batch 2, Phase 7).

``DecisionRequest`` deliberately carries ONLY this peer's own position plus its
belief grid over the opponent -- there is no field for the opponent's true
position, so a brain structurally cannot inspect it (enforced by a field
introspection test).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from police_peer.domain.belief_model import BeliefMap
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.positions import Direction, Position


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """Everything a brain is allowed to see when choosing this turn's move."""

    own_position: Position
    legal_directions: tuple[Direction, ...]
    belief: BeliefMap
    step: int
    rng: random.Random
    deadline: DeadlineTracker | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    """A brain's chosen action: a legal move, optional barrier, honest intent flag."""

    direction: Direction
    barrier: Position | None = None
    honest_intent: bool = True

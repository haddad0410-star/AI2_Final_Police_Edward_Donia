"""Cardinal-region <-> board-cell mapping for hint encode/decode (Batch 3.5
Task 5). The hint TEXT is the one field allowed to lie; a region word is
never a coordinate, only a cardinal cell-set the receiver can weigh as
uncertain evidence -- see
integration_lab/evidence/batch3_5/observation_pipeline_audit.md defects
C1/D1/D3.
"""

from __future__ import annotations

import random

from police_peer.domain.hints import HintIntent
from police_peer.domain.positions import Direction, Position

REGIONS: tuple[str, ...] = ("northern", "southern", "eastern", "western", "central")

_REGION_FOR_DIRECTION = {
    Direction.N: "northern",
    Direction.S: "southern",
    Direction.E: "eastern",
    Direction.W: "western",
    Direction.STAY: "central",
}


def region_for_direction(direction: Direction) -> str:
    """The TRUE cardinal region for a real move direction (never a lie)."""
    return _REGION_FOR_DIRECTION[direction]


def false_region_for_direction(direction: Direction, rng: random.Random) -> str:
    """A plausible but WRONG region word, for use only when intent is LIE."""
    true_region = region_for_direction(direction)
    candidates = [r for r in REGIONS if r != true_region]
    return rng.choice(candidates)


def region_for_intent(direction: Direction, intent: HintIntent, rng: random.Random) -> str:
    """The region word to embed in an outgoing hint: true when honest, a
    plausible wrong region when lying (never a raw coordinate either way)."""
    if intent is HintIntent.TRUTH:
        return region_for_direction(direction)
    return false_region_for_direction(direction, rng)


def parse_region_from_hint(hint_text: str) -> str | None:
    """Best-effort decode of a received hint's region word; ``None`` if the
    text is unparseable (treated as neutral, missing evidence)."""
    lowered = hint_text.lower()
    for word in REGIONS:
        if word in lowered:
            return word
    return None


def region_cells(region: str, grid_size: int) -> frozenset[Position]:
    """The set of board cells a cardinal region word legally refers to."""
    third = max(1, grid_size // 3)
    if region == "northern":
        return frozenset(Position(r, c) for r in range(0, third) for c in range(grid_size))
    if region == "southern":
        return frozenset(
            Position(r, c) for r in range(grid_size - third, grid_size) for c in range(grid_size)
        )
    if region == "western":
        return frozenset(Position(r, c) for r in range(grid_size) for c in range(0, third))
    if region == "eastern":
        return frozenset(
            Position(r, c) for r in range(grid_size) for c in range(grid_size - third, grid_size)
        )
    if region == "central":
        lo, hi = third, grid_size - third
        cells = frozenset(Position(r, c) for r in range(lo, hi) for c in range(lo, hi))
        return cells if cells else frozenset({Position(grid_size // 2, grid_size // 2)})
    return frozenset()

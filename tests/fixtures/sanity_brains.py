"""Batch 3.5 Task 9: deterministic, SCRIPTED brains for capture/barrier
sanity fixtures only -- never used in league play, never part of the
shipped strategy set. Configured via environment variables (private,
local-only, set by the launcher process -- never part of the wire
protocol) since the production strategy loader only ever passes
``weights``/``rng``, never fixture-specific constructor arguments. Move
selection is still pure Python; no LLM, no network.
"""

from __future__ import annotations

import os

from police_peer.domain.positions import Direction, Position
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.decision import Decision, DecisionRequest


class ScriptedPoliceBrain(PoliceBrainBase):
    """Plays the fixed direction sequence in ``SCRIPTED_POLICE_DIRECTIONS``
    (comma-separated, e.g. ``"E,STAY,STAY"``; repeats the last entry once
    exhausted). Optionally places a barrier at
    ``SCRIPTED_POLICE_BARRIER_STEP``/``SCRIPTED_POLICE_BARRIER_ROW``/``_COL``."""

    def _pick_move(self, request: DecisionRequest) -> Decision:
        raw = os.environ.get("SCRIPTED_POLICE_DIRECTIONS", "STAY")
        directions = [Direction(d.strip()) for d in raw.split(",") if d.strip()]
        index = min(request.step, len(directions) - 1)
        direction = directions[index]
        barrier = self._barrier_for_step(request.step)
        return Decision(direction=direction, barrier=barrier, honest_intent=True)

    @staticmethod
    def _barrier_for_step(step: int) -> Position | None:
        barrier_step = os.environ.get("SCRIPTED_POLICE_BARRIER_STEP")
        if barrier_step is None or int(barrier_step) != step:
            return None
        row = int(os.environ["SCRIPTED_POLICE_BARRIER_ROW"])
        col = int(os.environ["SCRIPTED_POLICE_BARRIER_COL"])
        return Position(row, col)

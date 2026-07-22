"""Batch 4A Task 7/8: per-step/sub-game reshaping helpers, split out of
``replay_view_model.py`` to keep both files under the 150-meaningful-line
cap. Pure data reshaping -- no cryptographic logic lives here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_THIEF_STATE_RE = re.compile(r"pos=(-?\d+),(-?\d+)")


@dataclass(frozen=True, slots=True)
class ReplayStep:
    step: int
    role: str
    position: tuple[int, int] | None
    move: str
    hint: str
    barrier_placed: tuple[int, int] | None
    capture_claim: tuple[int, int] | None
    claim_response: bool | None
    commit_hash_prefix: str


@dataclass(frozen=True, slots=True)
class ReplaySubGame:
    sub_game_number: int
    result: str
    winner: str | None
    police_score: int
    thief_score: int
    steps_total: int
    audit_ok: bool
    police_steps: tuple[ReplayStep, ...]
    thief_steps: tuple[ReplayStep, ...]
    barriers: tuple[tuple[int, int], ...]


def _position(step_dict: dict) -> tuple[int, int] | None:
    """Handles the current ``commitment/1`` top-level ``position`` field
    (both roles, since Batch 4B Task 3 unified the schema) and both legacy
    per-repo shapes for old evidence: Police's old
    ``state={"position": [r, c], ...}`` dict and Thief's old
    ``state="pos=R,C;visited=N"`` string -- a public JSON-artifact-format
    parse, not a code import."""
    if "position" in step_dict and step_dict["position"] is not None:
        row, col = step_dict["position"]
        return (row, col)
    state = step_dict.get("state")
    if isinstance(state, dict) and "position" in state:
        row, col = state["position"]
        return (row, col)
    if isinstance(state, str):
        m = _THIEF_STATE_RE.search(state)
        if m:
            return (int(m.group(1)), int(m.group(2)))
    return None


def _as_cell(value) -> tuple[int, int] | None:
    return (value[0], value[1]) if value is not None else None


def replay_step(raw: dict) -> ReplayStep:
    return ReplayStep(
        step=raw["step"],
        role=raw["role"],
        position=_position(raw),
        move=raw.get("move", ""),
        hint=raw.get("hint", ""),
        barrier_placed=_as_cell(raw.get("barrier_placed")),
        capture_claim=_as_cell(raw.get("capture_claim")),
        claim_response=raw.get("claim_response"),
        commit_hash_prefix=str(raw.get("commit_hash", ""))[:8],
    )


def steps_for(logs_by_number: dict, sub_game_number: int) -> tuple[ReplayStep, ...]:
    log = logs_by_number.get(sub_game_number)
    return tuple(replay_step(s) for s in (log or {}).get("steps", []))


def build_sub_game(entry: dict, police_logs: dict, thief_logs: dict) -> ReplaySubGame:
    n = entry["sub_game_number"]
    police_steps = steps_for(police_logs, n)
    thief_steps = steps_for(thief_logs, n)
    barriers = tuple(s.barrier_placed for s in police_steps if s.barrier_placed is not None)
    return ReplaySubGame(
        sub_game_number=n,
        result=entry["result"],
        winner=entry.get("winner"),
        police_score=entry["police_score"],
        thief_score=entry["thief_score"],
        steps_total=entry["steps"],
        audit_ok=entry.get("audit_ok", False),
        police_steps=police_steps,
        thief_steps=thief_steps,
        barriers=barriers,
    )

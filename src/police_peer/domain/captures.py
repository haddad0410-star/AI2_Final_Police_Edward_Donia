"""Capture-claim exchange and the final outcome of one sub-game."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from police_peer.domain.positions import Position
from police_peer.domain.roles import Role


@dataclass(frozen=True, slots=True)
class CaptureClaim:
    """Police claims the thief occupies `claimed_position` at `step`."""

    step: int
    claimed_position: Position


@dataclass(frozen=True, slots=True)
class CaptureResponse:
    """Thief's mandatory, honest reply to a CaptureClaim.

    `caught` must truthfully state whether the claim was correct; a false
    answer is cryptographically detectable at the final audit (implemented;
    see `domain/crypto/audit.py`, `tests/security/test_commit_reveal.py`)
    and is a disqualifying protocol violation, not merely a strategic option.
    """

    claimed_position: Position
    caught: bool


class SubGameResult(StrEnum):
    CAPTURE = "capture"
    SURVIVAL = "survival"
    TECHNICAL_LOSS = "technical_loss"


@dataclass(frozen=True, slots=True)
class SubGameOutcome:
    """The final, scored result of one sub-game."""

    result: SubGameResult
    winner: Role | None
    steps_taken: int
    police_score: int
    thief_score: int
    tie: bool = False

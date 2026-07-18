"""Series aggregation and the mutual final-agreement rule.

Per the book's rule, a disagreement between the two peers' declared totals
scores ZERO for both (never a silent average) -- represented here as an explicit
``disputed_zeroed`` outcome.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from police_peer.domain.captures import SubGameResult


@dataclass(frozen=True, slots=True)
class SubGameRecord:
    """One completed sub-game's scored, audited summary."""

    sub_game_number: int
    result: SubGameResult
    police_score: int
    thief_score: int
    steps: int
    audit_ok: bool


@dataclass(frozen=True, slots=True)
class FinalAgreement:
    """The end-of-series mutual-audit outcome and the totals it certifies."""

    agreed: bool
    status: str
    police_total: int
    thief_total: int


def aggregate(records: Iterable[SubGameRecord]) -> tuple[int, int]:
    """Sum per-sub-game scores into (police_total, thief_total)."""
    police = sum(r.police_score for r in records)
    thief = sum(r.thief_score for r in records)
    return police, thief


def resolve_final_agreement(
    our_police: int,
    our_thief: int,
    their_police: int | None,
    their_thief: int | None,
) -> FinalAgreement:
    """Certify agreed totals, or zero BOTH on any disagreement.

    ``their_*`` may be ``None`` for local self-play with no opposing declaration,
    in which case our own totals stand as provisional/unverified.
    """
    if their_police is None or their_thief is None:
        return FinalAgreement(False, "unverified_self_play", our_police, our_thief)
    if (our_police, our_thief) == (their_police, their_thief):
        return FinalAgreement(True, "agreed", our_police, our_thief)
    return FinalAgreement(False, "disputed_zeroed", 0, 0)

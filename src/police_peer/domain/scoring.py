"""Turn a sub-game's result into the (police_score, thief_score) pair defined
by the shared config's Scoring section (Appendix F Table 17)."""

from __future__ import annotations

from police_peer.domain.captures import SubGameResult
from police_peer.shared.config_sections import Scoring


def score_sub_game(result: SubGameResult, scoring: Scoring, tie: bool = False) -> tuple[int, int]:
    """Return (police_score, thief_score) for one completed sub-game."""
    if tie:
        return scoring.tie_score, scoring.tie_score
    if result is SubGameResult.CAPTURE:
        return scoring.capture_cop, scoring.capture_thief
    if result is SubGameResult.SURVIVAL:
        return scoring.survival_cop, scoring.survival_thief
    if result is SubGameResult.TECHNICAL_LOSS:
        return scoring.technical_loss, scoring.technical_loss
    raise ValueError(f"unknown sub-game result: {result!r}")

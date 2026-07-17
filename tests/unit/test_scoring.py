"""Tests for mapping a sub-game result to the shared config's score constants."""

from __future__ import annotations

from police_peer.domain.captures import SubGameResult
from police_peer.domain.scoring import score_sub_game
from police_peer.shared.config_sections import Scoring

SCORING = Scoring(
    capture_cop=20,
    capture_thief=5,
    survival_cop=5,
    survival_thief=10,
    tie_score=2,
    technical_loss=0,
)


def test_capture_scores() -> None:
    assert score_sub_game(SubGameResult.CAPTURE, SCORING) == (20, 5)


def test_survival_scores() -> None:
    assert score_sub_game(SubGameResult.SURVIVAL, SCORING) == (5, 10)


def test_technical_loss_scores() -> None:
    assert score_sub_game(SubGameResult.TECHNICAL_LOSS, SCORING) == (0, 0)


def test_tie_overrides_result() -> None:
    assert score_sub_game(SubGameResult.CAPTURE, SCORING, tie=True) == (2, 2)

"""summary_exit_code must fail a series that finished locally but never
reached a real, matching bilateral agreement -- never just technical loss."""

from __future__ import annotations

from police_peer.sdk.game_runner import summary_exit_code

_BASE = {"mode": "run-series", "terminated_reason": "completed", "final_state": "series_complete"}


def test_agreed_completed_series_exits_zero() -> None:
    summary = {**_BASE, "agreed": True, "agreement_status": "agreed"}
    assert summary_exit_code(summary) == 0


def test_disputed_zeroed_exits_nonzero() -> None:
    summary = {**_BASE, "agreed": False, "agreement_status": "disputed_zeroed"}
    assert summary_exit_code(summary) == 1


def test_unverified_self_play_exits_nonzero() -> None:
    summary = {**_BASE, "agreed": False, "agreement_status": "unverified_self_play"}
    assert summary_exit_code(summary) == 1


def test_agreed_false_without_agreement_status_exits_nonzero() -> None:
    summary = {**_BASE, "agreed": False}
    assert summary_exit_code(summary) == 1


def test_technical_loss_still_exits_nonzero_regardless_of_agreement() -> None:
    summary = {**_BASE, "result": "technical_loss", "agreed": True, "agreement_status": "agreed"}
    assert summary_exit_code(summary) == 1


def test_incomplete_termination_still_exits_nonzero() -> None:
    summary = {**_BASE, "terminated_reason": "opponent_unavailable", "agreed": True}
    assert summary_exit_code(summary) == 1


def test_run_subgame_summary_with_no_agreement_fields_is_unaffected() -> None:
    summary = {"mode": "run-subgame", "result": "capture", "reason": "captured"}
    assert summary_exit_code(summary) == 0

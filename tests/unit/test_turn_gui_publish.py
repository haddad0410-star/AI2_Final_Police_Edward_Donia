"""Batch 4B: proves the GUI protocol-status fields (commit_sent/ack_received/
reveal_sent/reveal_received) are read from a real ``TechnicalFailure``'s own
per-substep progress, never hardcoded or collapsed onto one pass/fail flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from police_peer.services import gui_sink
from police_peer.services import turn_gui_publish as gui
from police_peer.services.gui_events import TurnExchangeEvent
from police_peer.services.transport import TechnicalFailure


@dataclass
class _FakeBoard:
    barriers: list = field(default_factory=list)


@dataclass
class _FakeState:
    sub_game_number: int = 1
    step: int = 3
    board: _FakeBoard = field(default_factory=_FakeBoard)


def _captured(fn) -> TurnExchangeEvent:
    events: list = []
    gui_sink.set_sink(events.append)
    try:
        fn()
    finally:
        gui_sink.clear_sink()
    assert len(events) == 1
    assert isinstance(events[0], TurnExchangeEvent)
    return events[0]


def test_exchange_ok_reports_all_four_true() -> None:
    event = _captured(lambda: gui.exchange_ok(_FakeState(), "hint", "a" * 64, "TURN_VERIFIED"))
    assert (event.commit_sent, event.ack_received, event.reveal_sent, event.reveal_received) == (
        True,
        True,
        True,
        True,
    )


def test_exchange_failed_reflects_real_partial_progress_not_hardcoded() -> None:
    failure = TechnicalFailure(
        "opponent rejected our reveal: {}", commit_sent=True, commit_acked=True, reveal_sent=True
    )
    event = _captured(lambda: gui.exchange_failed(_FakeState(), "a" * 64, "ERROR", failure))
    assert (event.commit_sent, event.ack_received, event.reveal_sent, event.reveal_received) == (
        True,
        True,
        True,
        False,
    )


def test_exchange_failed_with_no_progress_claims_none() -> None:
    """A non-exchange runtime fault (no TechnicalFailure available) must
    claim none of the four -- never guess success from the error path."""
    event = _captured(lambda: gui.exchange_failed(_FakeState(), "a" * 64, "ERROR", None))
    assert (event.commit_sent, event.ack_received, event.reveal_sent, event.reveal_received) == (
        False,
        False,
        False,
        False,
    )


def test_exchange_failed_distinguishes_early_from_late_failure() -> None:
    """Two different real failures at two different points must publish two
    different real event signatures."""
    early = TechnicalFailure("opponent rejected our commitment: {}", commit_sent=True)
    late = TechnicalFailure(
        "opponent unreachable: refused", commit_sent=True, commit_acked=True, reveal_sent=True
    )
    early_event = _captured(lambda: gui.exchange_failed(_FakeState(), "a" * 64, "ERROR", early))
    late_event = _captured(lambda: gui.exchange_failed(_FakeState(), "a" * 64, "ERROR", late))
    early_flags = (early_event.commit_sent, early_event.ack_received, early_event.reveal_sent)
    late_flags = (late_event.commit_sent, late_event.ack_received, late_event.reveal_sent)
    assert early_flags != late_flags
    assert early_flags == (True, False, False)
    assert late_flags == (True, True, True)

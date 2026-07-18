"""Phase 3: Watchdog escalation ladder, all with a fake clock (no real sleeps)."""

from __future__ import annotations

from police_peer.domain.watchdog import Watchdog, WatchdogDecision


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_normal_operation_continues() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=3, now_fn=clock)
    clock.advance(10.0)
    assert wd.assess().decision is WatchdogDecision.CONTINUE


def test_progress_resets_stall_window() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=3, now_fn=clock)
    clock.advance(50.0)
    wd.note_progress()
    clock.advance(50.0)  # 50s since last progress -- still under 60s
    assert wd.stalled() is False
    assert wd.assess().decision is WatchdogDecision.CONTINUE


def test_watchdog_activation_on_stall_requests_graceful_first() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=3, now_fn=clock)
    clock.advance(61.0)
    assert wd.stalled() is True
    first = wd.assess()
    assert first.decision is WatchdogDecision.GRACEFUL_SHUTDOWN
    assert first.escalations == 1


def test_retry_exhaustion_yields_technical_loss() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=3, now_fn=clock)
    clock.advance(61.0)
    decisions = [wd.assess().decision for _ in range(4)]
    assert decisions == [
        WatchdogDecision.GRACEFUL_SHUTDOWN,
        WatchdogDecision.ESCALATE,
        WatchdogDecision.ESCALATE,
        WatchdogDecision.TECHNICAL_LOSS,
    ]


def test_dead_subprocess_feeds_escalation_ladder() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=1, now_fn=clock, is_subprocess_alive=lambda: False)
    first = wd.assess()
    assert first.decision is WatchdogDecision.GRACEFUL_SHUTDOWN
    assert "not alive" in first.reason
    assert wd.assess().decision is WatchdogDecision.TECHNICAL_LOSS  # max_retries=1 exhausted


def test_opponent_unavailable_simulated_via_dead_probe() -> None:
    """An 'opponent unavailable' local health probe returning False escalates."""
    clock = FakeClock()
    unavailable = Watchdog(30.0, max_retries=3, now_fn=clock, is_subprocess_alive=lambda: False)
    assert unavailable.assess().decision is WatchdogDecision.GRACEFUL_SHUTDOWN


def test_malformed_response_loop_bounded() -> None:
    """Repeated malformed replies (no progress noted) must not loop forever."""
    clock = FakeClock()
    wd = Watchdog(5.0, max_retries=2, now_fn=clock)
    clock.advance(6.0)
    seen = []
    for _ in range(10):
        assessment = wd.assess()
        seen.append(assessment.decision)
        if assessment.decision is WatchdogDecision.TECHNICAL_LOSS:
            break
    assert seen[-1] is WatchdogDecision.TECHNICAL_LOSS
    assert len(seen) == 3  # graceful, escalate, technical_loss -- bounded


def test_clean_shutdown_when_healthy_never_escalates() -> None:
    clock = FakeClock()
    wd = Watchdog(60.0, max_retries=3, now_fn=clock)
    for _ in range(5):
        clock.advance(1.0)
        wd.note_progress()
    assert wd.assess().escalations == 0

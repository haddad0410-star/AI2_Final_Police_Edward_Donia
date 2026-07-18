"""Phase 3: DeadlineTracker with an injected fake clock (no real sleeps)."""

from __future__ import annotations

import pytest

from police_peer.domain.deadline import DeadlineTracker


class FakeClock:
    """A controllable monotonic clock for deterministic deadline tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_remaining_before_start_is_full_budget() -> None:
    clock = FakeClock()
    d = DeadlineTracker(30.0, now_fn=clock)
    assert d.remaining() == 30.0
    assert d.started is False
    assert d.elapsed() == 0.0


def test_response_within_deadline() -> None:
    clock = FakeClock()
    d = DeadlineTracker(30.0, now_fn=clock).start()
    clock.advance(10.0)
    assert d.elapsed() == 10.0
    assert d.remaining() == 20.0
    assert d.expired() is False


def test_response_after_deadline_clamps_to_zero() -> None:
    clock = FakeClock()
    d = DeadlineTracker(30.0, now_fn=clock).start()
    clock.advance(45.0)
    assert d.remaining() == 0.0  # clamped, never negative
    assert d.expired() is True


def test_child_deadline_cannot_outlive_parent() -> None:
    clock = FakeClock()
    parent = DeadlineTracker(30.0, now_fn=clock).start()
    clock.advance(25.0)  # 5s left on the parent
    child = parent.child(20.0)  # asked for 20s but only 5 remain
    assert child.remaining() == 5.0
    assert child.started is True


def test_child_deadline_smaller_request_wins() -> None:
    clock = FakeClock()
    parent = DeadlineTracker(60.0, now_fn=clock).start()
    child = parent.child(2.5)
    assert child.remaining() == 2.5


def test_negative_budget_rejected() -> None:
    with pytest.raises(ValueError):
        DeadlineTracker(-1.0)


def test_restart_resets_countdown() -> None:
    clock = FakeClock()
    d = DeadlineTracker(30.0, now_fn=clock).start()
    clock.advance(30.0)
    assert d.expired() is True
    d.start()
    assert d.remaining() == 30.0
    assert d.expired() is False

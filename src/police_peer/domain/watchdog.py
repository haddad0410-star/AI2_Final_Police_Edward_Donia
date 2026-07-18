"""Watchdog: bounded local-runtime health monitor with an escalation ladder.

Detects a stalled peer (no progress within ``watchdog_timeout_sec``) or a dead
local subprocess, then escalates through a FIXED, bounded ladder -- graceful
shutdown first, then escalate, and finally a technical-loss outcome once the
retry budget is exhausted. The bound on retries is what prevents an infinite
restart loop. Uses ``time.monotonic`` via an injectable ``now_fn`` so tests
never sleep in real time.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from police_peer.domain.deadline import DeadlineTracker


class WatchdogDecision(StrEnum):
    """The action the watchdog recommends for the current assessment."""

    CONTINUE = "continue"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"
    ESCALATE = "escalate"
    TECHNICAL_LOSS = "technical_loss"


@dataclass(frozen=True, slots=True)
class WatchdogAssessment:
    """The outcome of one :meth:`Watchdog.assess` call."""

    decision: WatchdogDecision
    reason: str
    escalations: int


class Watchdog:
    """A stall/death detector that escalates at most ``max_retries`` times."""

    def __init__(
        self,
        timeout_seconds: float,
        max_retries: int,
        now_fn: Callable[[], float] = time.monotonic,
        is_subprocess_alive: Callable[[], bool] | None = None,
    ) -> None:
        self._timeout = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._now = now_fn
        self._alive = is_subprocess_alive
        self._deadline = DeadlineTracker(timeout_seconds, now_fn=now_fn).start()
        self._escalations = 0

    def note_progress(self) -> None:
        """Record forward progress: resets the stall clock and escalation count."""
        self._deadline = DeadlineTracker(self._timeout, now_fn=self._now).start()
        self._escalations = 0

    def stalled(self) -> bool:
        """True once no progress has been noted within the timeout window."""
        return self._deadline.expired()

    def _escalate(self, reason: str) -> WatchdogAssessment:
        self._escalations += 1
        if self._escalations > self._max_retries:
            return WatchdogAssessment(WatchdogDecision.TECHNICAL_LOSS, reason, self._escalations)
        if self._escalations == 1:
            return WatchdogAssessment(WatchdogDecision.GRACEFUL_SHUTDOWN, reason, self._escalations)
        return WatchdogAssessment(WatchdogDecision.ESCALATE, reason, self._escalations)

    def assess(self) -> WatchdogAssessment:
        """Assess health once and recommend an action.

        A dead subprocess or a stall both feed the same bounded escalation
        ladder; a healthy, progressing peer returns ``CONTINUE`` without
        consuming any of the retry budget.
        """
        if self._alive is not None and not self._alive():
            return self._escalate("local subprocess is not alive")
        if self.stalled():
            return self._escalate(f"no progress within {self._timeout:g}s stall window")
        return WatchdogAssessment(WatchdogDecision.CONTINUE, "healthy", self._escalations)

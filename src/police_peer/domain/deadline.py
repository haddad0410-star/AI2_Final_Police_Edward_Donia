"""DeadlineTracker: a monotonic per-phase time budget.

Uses ``time.monotonic`` by default (never wall-clock, which can jump backwards
on NTP corrections). Tests inject a fake clock via ``now_fn`` so no test ever
sleeps for a real 30 or 60 seconds.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class DeadlineTracker:
    """A single, restartable countdown over a fixed ``budget_seconds``."""

    def __init__(self, budget_seconds: float, now_fn: Callable[[], float] = time.monotonic) -> None:
        if budget_seconds < 0:
            raise ValueError("budget_seconds must be non-negative")
        self._budget = float(budget_seconds)
        self._now = now_fn
        self._start: float | None = None

    def start(self) -> DeadlineTracker:
        """(Re)start the countdown from the current monotonic instant."""
        self._start = self._now()
        return self

    @property
    def started(self) -> bool:
        """True once :meth:`start` has been called."""
        return self._start is not None

    def elapsed(self) -> float:
        """Seconds since :meth:`start` (0.0 before the tracker is started)."""
        if self._start is None:
            return 0.0
        return max(0.0, self._now() - self._start)

    def remaining(self) -> float:
        """Seconds of budget left, clamped so it never goes negative."""
        if self._start is None:
            return self._budget
        return max(0.0, self._budget - self.elapsed())

    def expired(self) -> bool:
        """True once the budget is fully spent."""
        return self.started and self.remaining() <= 0.0

    def child(self, budget_seconds: float) -> DeadlineTracker:
        """Allocate a phase sub-deadline that cannot outlive this parent.

        The child's budget is the smaller of ``budget_seconds`` and the
        parent's ``remaining()``, and it is returned already started so a
        strategy/phase can never be handed more time than the parent has left.
        """
        allocated = min(float(budget_seconds), self.remaining())
        return DeadlineTracker(allocated, now_fn=self._now).start()

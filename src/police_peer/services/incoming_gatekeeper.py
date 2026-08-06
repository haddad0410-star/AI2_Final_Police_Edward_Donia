"""Gate A1: incoming-request Gatekeeper for the public HTTP/MCP surface.

Independent of ``infrastructure/gmail_gatekeeper.py``'s ``Gatekeeper`` --
own class, own mutable state, never shared -- but config-driven from the
same ``RateLimitsConfig`` shape (``rate_limits.json``'s top-level block,
already documented as applying to "MCP calls" too, not just Gmail), so the
binding minimums (30/min, 2 concurrent, queue 100) are never hardcoded a
second time.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import deque

from police_peer.shared.rate_limits_model import RateLimitsConfig


class OverloadedError(Exception):
    """Raised by :meth:`IncomingGatekeeper.slot` when the request must be
    rejected honestly (rate exceeded or queue full) -- the caller never
    proceeds to invoke a tool when this is raised."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class IncomingGatekeeper:
    """Bounds concurrent in-flight requests (semaphore) and the rolling
    per-minute request rate (sliding window), honestly rejecting anything
    beyond the configured minimums rather than silently queuing forever."""

    def __init__(self, config: RateLimitsConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.concurrent_requests)
        self._recent: deque[float] = deque()
        self._queue_depth = 0

    def _within_rate(self) -> bool:
        now = time.monotonic()
        while self._recent and now - self._recent[0] > 60.0:
            self._recent.popleft()
        return len(self._recent) < self._config.requests_per_minute

    @contextlib.asynccontextmanager
    async def slot(self):
        """Reject immediately (before touching the semaphore) if the queue
        is full or the rate is already exceeded; otherwise hold one
        concurrency slot for the duration of the ``with`` body. Cancellation,
        a raised exception, or a timeout inside the body all still run the
        ``finally`` below, so a slot is never leaked."""
        if self._queue_depth >= self._config.queue_depth:
            raise OverloadedError("queue_depth_exceeded")
        if not self._within_rate():
            raise OverloadedError("rate_limit_exceeded")
        self._queue_depth += 1
        self._recent.append(time.monotonic())
        try:
            async with self._semaphore:
                yield
        finally:
            self._queue_depth -= 1

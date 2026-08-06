"""Gate A1 correction: proactive OUTBOUND pacing toward a ``--public``
opponent.

Appendix F Table 19's own worked context (this project's ``rate_limits.json``
``_note``: "applies to this peer's own outbound API calls") makes the
Gatekeeper fundamentally a self-throttling mechanism: a well-behaved client
paces its own calls so it never needs the receiver to reject anything. This
complements (does not replace) the server-side incoming Gatekeeper, which
remains a defensive backstop against a misbehaving/malicious caller.

Unlike :class:`~police_peer.services.incoming_gatekeeper.IncomingGatekeeper`
(which REJECTS once the budget is exhausted), :class:`OutboundPacer` WAITS --
a client is fully in control of its own cadence, so the correct behavior is
to hold back the next call rather than fire a burst and rely on 429/overload
responses. The wait is always bounded (at most one 60s window), so a whole
series is bounded too, never an infinite stall.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import deque

from police_peer.shared.rate_limits_model import RateLimitsConfig


class OutboundPacer:
    """Paces outbound calls to at most ``requests_per_minute`` per rolling
    60s window and at most ``concurrent_requests`` in flight at once --
    the same binding minimums the opponent's own incoming Gatekeeper
    enforces, so a compliant client should rarely if ever be rejected."""

    def __init__(self, config: RateLimitsConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.concurrent_requests)
        self._recent: deque[float] = deque()
        self._window_lock = asyncio.Lock()

    async def _await_rate_slot(self) -> None:
        while True:
            async with self._window_lock:
                now = time.monotonic()
                while self._recent and now - self._recent[0] > 60.0:
                    self._recent.popleft()
                if len(self._recent) < self._config.requests_per_minute:
                    self._recent.append(now)
                    return
                wait_for = 60.0 - (now - self._recent[0])
            await asyncio.sleep(max(wait_for, 0.01))

    @contextlib.asynccontextmanager
    async def slot(self):
        """Wait (bounded, never unbounded) for a rate/concurrency slot, then
        hold it for the duration of the ``with`` body."""
        await self._await_rate_slot()
        async with self._semaphore:
            yield

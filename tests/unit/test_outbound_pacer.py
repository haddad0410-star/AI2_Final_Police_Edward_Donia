"""Gate A1 correction: OutboundPacer -- proactive client-side pacing. Waits
(never rejects) for a rate/concurrency slot, so a compliant client never
needs to rely on repeated overload responses."""

from __future__ import annotations

import asyncio
import time

from police_peer.infrastructure.outbound_pacer import OutboundPacer
from police_peer.shared.rate_limits_model import RateLimitsConfig


def _config(**overrides) -> RateLimitsConfig:
    base = {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    base.update(overrides)
    return RateLimitsConfig(**base)


def test_calls_within_the_configured_rate_all_proceed_without_waiting() -> None:
    async def scenario() -> float:
        pacer = OutboundPacer(_config(requests_per_minute=30))
        start = time.monotonic()
        for _ in range(30):
            async with pacer.slot():
                pass
        return time.monotonic() - start

    assert asyncio.run(scenario()) < 1.0


def test_excess_call_waits_for_a_rate_slot_instead_of_being_rejected() -> None:
    async def scenario() -> float:
        pacer = OutboundPacer(_config(requests_per_minute=2))
        pacer._recent.append(time.monotonic())
        pacer._recent.append(time.monotonic())
        # Both slots are "full" but will age out in ~0.05s -- proves the
        # pacer WAITS for real capacity rather than rejecting outright.
        pacer._recent[0] -= 60.0 - 0.05
        pacer._recent[1] -= 60.0 - 0.05
        start = time.monotonic()
        async with pacer.slot():
            pass
        return time.monotonic() - start

    elapsed = asyncio.run(scenario())
    assert 0.0 < elapsed < 5.0


def test_at_most_concurrent_requests_calls_run_at_once() -> None:
    async def scenario() -> int:
        pacer = OutboundPacer(_config(concurrent_requests=2, requests_per_minute=1000))
        active = 0
        peak = 0
        lock = asyncio.Lock()

        async def call() -> None:
            nonlocal active, peak
            async with pacer.slot():
                async with lock:
                    active += 1
                    peak = max(peak, active)
                await asyncio.sleep(0.05)
                async with lock:
                    active -= 1

        await asyncio.gather(*(call() for _ in range(5)))
        return peak

    assert asyncio.run(scenario()) == 2


def test_pacing_prevents_an_uncontrolled_burst() -> None:
    """10 calls at requests_per_minute=5 must take real elapsed time (the
    excess calls genuinely wait for the window to advance), not fire all at
    once."""

    async def scenario() -> float:
        pacer = OutboundPacer(_config(requests_per_minute=5))
        # Pre-seed the window so it is already at capacity, ageing out
        # quickly, keeping the test fast while still proving real waiting.
        now = time.monotonic()
        for i in range(5):
            pacer._recent.append(now - (60.0 - 0.1 * (i + 1)))
        start = time.monotonic()
        for _ in range(5):
            async with pacer.slot():
                pass
        return time.monotonic() - start

    elapsed = asyncio.run(scenario())
    assert elapsed > 0.05

"""Gate A1: IncomingGatekeeper -- concurrency/rate bounds, independent of
the Gmail Gatekeeper's own mutable state."""

from __future__ import annotations

import asyncio

import pytest

from police_peer.services.incoming_gatekeeper import IncomingGatekeeper, OverloadedError
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


def test_requests_within_configured_rate_all_succeed() -> None:
    async def scenario() -> int:
        gk = IncomingGatekeeper(_config(requests_per_minute=30))
        count = 0
        for _ in range(30):
            async with gk.slot():
                count += 1
        return count

    assert asyncio.run(scenario()) == 30


def test_excess_request_is_rejected_honestly() -> None:
    async def scenario() -> str:
        gk = IncomingGatekeeper(_config(requests_per_minute=2))
        async with gk.slot():
            pass
        async with gk.slot():
            pass
        try:
            async with gk.slot():
                pass
        except OverloadedError as exc:
            return exc.reason
        return "not_rejected"

    assert asyncio.run(scenario()) == "rate_limit_exceeded"


def test_queue_capacity_is_bounded() -> None:
    async def scenario() -> str:
        gk = IncomingGatekeeper(_config(requests_per_minute=1000, queue_depth=1))
        gk._queue_depth = 1  # simulate one already-admitted in-flight request
        try:
            async with gk.slot():
                pass
        except OverloadedError as exc:
            return exc.reason
        return "not_rejected"

    assert asyncio.run(scenario()) == "queue_depth_exceeded"


def test_at_most_two_concurrent_handlers_run_at_once() -> None:
    async def scenario() -> int:
        gk = IncomingGatekeeper(_config(concurrent_requests=2, requests_per_minute=1000))
        active = 0
        peak = 0
        lock = asyncio.Lock()

        async def handler() -> None:
            nonlocal active, peak
            async with gk.slot():
                async with lock:
                    active += 1
                    peak = max(peak, active)
                await asyncio.sleep(0.05)
                async with lock:
                    active -= 1

        await asyncio.gather(*(handler() for _ in range(5)))
        return peak

    assert asyncio.run(scenario()) == 2


def test_cancelled_request_releases_its_slot() -> None:
    async def scenario() -> int:
        gk = IncomingGatekeeper(_config(concurrent_requests=1, requests_per_minute=1000))

        async def hang_forever() -> None:
            async with gk.slot():
                await asyncio.sleep(10)

        task = asyncio.create_task(hang_forever())
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # If the slot leaked, this would deadlock/hang -- it must succeed promptly.
        async with gk.slot():
            pass
        return gk._queue_depth

    assert asyncio.run(scenario()) == 0


def test_failed_handler_releases_its_slot() -> None:
    async def scenario() -> int:
        gk = IncomingGatekeeper(_config(concurrent_requests=1, requests_per_minute=1000))
        with pytest.raises(ValueError):
            async with gk.slot():
                raise ValueError("boom")
        async with gk.slot():
            pass
        return gk._queue_depth

    assert asyncio.run(scenario()) == 0


def test_timeout_releases_its_slot() -> None:
    async def scenario() -> int:
        gk = IncomingGatekeeper(_config(concurrent_requests=1, requests_per_minute=1000))
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.02):
                async with gk.slot():
                    await asyncio.sleep(10)
        async with gk.slot():
            pass
        return gk._queue_depth

    assert asyncio.run(scenario()) == 0


def test_config_values_come_from_the_shared_config_object_not_hardcoded() -> None:
    gk = IncomingGatekeeper(_config(requests_per_minute=7, concurrent_requests=1, queue_depth=1))
    assert gk._config.requests_per_minute == 7
    assert gk._semaphore._value == 1

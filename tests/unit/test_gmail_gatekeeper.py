"""Batch 4A Task 11: Gatekeeper tests. Always a mocked send function --
never a real Gmail API call. Follows this repo's existing convention
(``tests/unit/test_http_transport.py``) of plain ``def test_...`` wrapping
``asyncio.run(...)`` rather than a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio

from police_peer.infrastructure.gmail_gatekeeper import Gatekeeper, RateLimitedError
from police_peer.shared.rate_limits_model import RateLimitsConfig


def _config(**overrides) -> RateLimitsConfig:
    base = {
        "requests_per_minute": 5,
        "concurrent_requests": 2,
        "retry_backoff_sec": 0,
        "max_retries": 2,
        "queue_depth": 3,
    }
    base.update(overrides)
    return RateLimitsConfig(**base)


def test_successful_send() -> None:
    calls = []

    async def send_fn(message):
        calls.append(message)
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-1")

    result = asyncio.run(run())
    assert result.ok is True
    assert result.attempts == 1
    assert len(calls) == 1


def test_duplicate_idempotency_key_suppressed() -> None:
    calls = []

    async def send_fn(message):
        calls.append(message)
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(), send_fn)
        await gk.submit({"raw": "x"}, idempotency_key="game-1")
        return await gk.submit({"raw": "x"}, idempotency_key="game-1")

    result2 = asyncio.run(run())
    assert result2.duplicate is True
    assert result2.ok is True
    assert len(calls) == 1


def test_429_retries_then_succeeds() -> None:
    attempts = {"n": 0}

    async def send_fn(message):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RateLimitedError("429")
        return {"id": "ok"}

    async def run():
        gk = Gatekeeper(_config(retry_backoff_sec=0), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-2")

    result = asyncio.run(run())
    assert result.ok is True
    assert result.attempts == 2


def test_429_exhausts_retries_and_fails() -> None:
    async def send_fn(message):
        raise RateLimitedError("429")

    async def run():
        gk = Gatekeeper(_config(max_retries=1, retry_backoff_sec=0), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-3")

    result = asyncio.run(run())
    assert result.ok is False
    assert result.error == "429_retries_exhausted"


def test_no_infinite_retry_loop() -> None:
    """Bounded by max_retries -- never loops forever."""
    attempts = {"n": 0}

    async def send_fn(message):
        attempts["n"] += 1
        raise RateLimitedError("429")

    async def run():
        gk = Gatekeeper(_config(max_retries=3, retry_backoff_sec=0), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-4")

    result = asyncio.run(run())
    assert result.ok is False
    assert attempts["n"] == 4  # 1 initial + 3 retries, then stop


def test_timeout_is_bounded_not_hung() -> None:
    async def send_fn(message):
        await asyncio.sleep(10)

    async def run():
        gk = Gatekeeper(_config(), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-5", timeout=0.05)

    result = asyncio.run(run())
    assert result.ok is False
    assert result.error == "timeout"


def test_queue_depth_limit_rejects_when_full() -> None:
    async def send_fn(message):
        await asyncio.sleep(0.2)
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(queue_depth=1, concurrent_requests=1), send_fn)
        task1 = asyncio.create_task(gk.submit({"raw": "1"}, idempotency_key="a"))
        await asyncio.sleep(0.01)
        result2 = await gk.submit({"raw": "2"}, idempotency_key="b")
        await task1
        return result2

    result2 = asyncio.run(run())
    assert result2.ok is False
    assert result2.error == "queue_depth_exceeded"


def test_rate_limit_per_minute_enforced() -> None:
    async def send_fn(message):
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(requests_per_minute=1), send_fn)
        r1 = await gk.submit({"raw": "1"}, idempotency_key="a")
        r2 = await gk.submit({"raw": "2"}, idempotency_key="b")
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1.ok is True
    assert r2.ok is False
    assert r2.error == "rate_limit_exceeded"


def test_concurrency_limit_respected() -> None:
    in_flight = {"current": 0, "max": 0}

    async def send_fn(message):
        in_flight["current"] += 1
        in_flight["max"] = max(in_flight["max"], in_flight["current"])
        await asyncio.sleep(0.05)
        in_flight["current"] -= 1
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(concurrent_requests=2, queue_depth=10), send_fn)
        await asyncio.gather(
            gk.submit({"raw": "1"}, idempotency_key="a"),
            gk.submit({"raw": "2"}, idempotency_key="b"),
            gk.submit({"raw": "3"}, idempotency_key="c"),
        )

    asyncio.run(run())
    assert in_flight["max"] <= 2


def test_structured_result_shape() -> None:
    async def send_fn(message):
        return {"id": "1"}

    async def run():
        gk = Gatekeeper(_config(), send_fn)
        return await gk.submit({"raw": "x"}, idempotency_key="game-6")

    result = asyncio.run(run())
    assert hasattr(result, "ok")
    assert hasattr(result, "attempts")
    assert hasattr(result, "duplicate")
    assert hasattr(result, "error")

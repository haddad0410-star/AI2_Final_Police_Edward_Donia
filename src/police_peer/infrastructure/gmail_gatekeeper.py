"""Batch 4A Task 11: the Gatekeeper/token-bucket architecture ALL Gmail
sends must route through. Built on the existing private
``rate_limits.json``/``RateLimitsConfig`` (Appendix F Table 19 minimums).
Never calls a real Gmail API itself -- ``send_fn`` is injected, always
mocked in tests.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol

from police_peer.shared.rate_limits_model import RateLimitsConfig


class RateLimitedError(Exception):
    """Raised by ``send_fn`` to signal a real (or simulated) HTTP 429."""


@dataclass(frozen=True, slots=True)
class GatekeeperResult:
    ok: bool
    attempts: int
    duplicate: bool
    error: str | None


class SendFn(Protocol):
    async def __call__(self, message: dict) -> dict: ...


class Gatekeeper:
    """Token-bucket rate limiting + bounded retries + idempotency for
    Gmail sends. Every send passes through here, never around it."""

    def __init__(self, config: RateLimitsConfig, send_fn: SendFn) -> None:
        self._config = config
        self._send_fn = send_fn
        self._semaphore = asyncio.Semaphore(config.concurrent_requests)
        self._sent_keys: set[str] = set()
        self._recent_sends: deque[float] = deque()
        self._queue_depth = 0

    def _within_rate(self) -> bool:
        now = time.monotonic()
        while self._recent_sends and now - self._recent_sends[0] > 60.0:
            self._recent_sends.popleft()
        return len(self._recent_sends) < self._config.requests_per_minute

    async def submit(
        self, message: dict, idempotency_key: str, timeout: float = 30.0
    ) -> GatekeeperResult:
        if idempotency_key in self._sent_keys:
            return GatekeeperResult(ok=True, attempts=0, duplicate=True, error=None)
        if self._queue_depth >= self._config.queue_depth:
            return GatekeeperResult(
                ok=False, attempts=0, duplicate=False, error="queue_depth_exceeded"
            )
        if not self._within_rate():
            return GatekeeperResult(
                ok=False, attempts=0, duplicate=False, error="rate_limit_exceeded"
            )
        self._queue_depth += 1
        try:
            async with self._semaphore:
                return await self._attempt(message, idempotency_key, timeout)
        finally:
            self._queue_depth -= 1

    async def _attempt(
        self, message: dict, idempotency_key: str, timeout: float
    ) -> GatekeeperResult:
        attempt = 0
        while attempt <= self._config.max_retries:
            attempt += 1
            self._recent_sends.append(time.monotonic())
            try:
                await asyncio.wait_for(self._send_fn(message), timeout=timeout)
            except RateLimitedError:
                if attempt > self._config.max_retries:
                    return GatekeeperResult(
                        ok=False, attempts=attempt, duplicate=False, error="429_retries_exhausted"
                    )
                await asyncio.sleep(self._config.retry_backoff_sec * attempt)
                continue
            except TimeoutError:
                return GatekeeperResult(
                    ok=False, attempts=attempt, duplicate=False, error="timeout"
                )
            self._sent_keys.add(idempotency_key)
            return GatekeeperResult(ok=True, attempts=attempt, duplicate=False, error=None)
        return GatekeeperResult(
            ok=False, attempts=attempt, duplicate=False, error="max_retries_exceeded"
        )

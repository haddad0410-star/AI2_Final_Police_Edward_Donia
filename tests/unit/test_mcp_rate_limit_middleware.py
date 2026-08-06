"""Gate A1 correction: McpRateLimitMiddleware -- direct unit-level proof
that it hooks ``on_call_tool`` (one accounting event per logical tool call),
excludes ``health``, and raises the distinct overload error before the
wrapped tool handler runs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from fastmcp.server.middleware import MiddlewareContext

from police_peer.infrastructure.mcp_rate_limit_middleware import (
    OVERLOAD_ERROR_CODE,
    McpOverloadError,
    McpRateLimitMiddleware,
)
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
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


@dataclass
class _FakeMessage:
    name: str


def _ctx(tool_name: str) -> MiddlewareContext:
    return MiddlewareContext(message=_FakeMessage(tool_name), method="tools/call", type="request")


def test_health_bypasses_the_gatekeeper_entirely() -> None:
    async def scenario() -> int:
        config = _config(requests_per_minute=1)
        gk = IncomingGatekeeper(config)
        mw = McpRateLimitMiddleware(gk, config)
        for _ in range(5):
            await mw.on_call_tool(_ctx("health"), lambda _c: asyncio.sleep(0, result="ok"))
        return len(gk._recent)

    assert asyncio.run(scenario()) == 0


def test_non_health_tool_charges_the_gatekeeper_once() -> None:
    async def scenario() -> int:
        config = _config(requests_per_minute=30)
        gk = IncomingGatekeeper(config)
        mw = McpRateLimitMiddleware(gk, config)
        await mw.on_call_tool(_ctx("negotiate"), lambda _c: asyncio.sleep(0, result="ok"))
        return len(gk._recent)

    assert asyncio.run(scenario()) == 1


def test_overload_raises_before_the_handler_runs() -> None:
    async def scenario() -> tuple[bool, bool]:
        config = _config(requests_per_minute=1)
        gk = IncomingGatekeeper(config)
        mw = McpRateLimitMiddleware(gk, config)
        handler_ran = {"first": False, "second": False}

        async def handler_first(_c):
            handler_ran["first"] = True
            return "ok"

        async def handler_second(_c):
            handler_ran["second"] = True
            return "ok"

        await mw.on_call_tool(_ctx("negotiate"), handler_first)
        with pytest.raises(McpOverloadError):
            await mw.on_call_tool(_ctx("negotiate"), handler_second)
        return handler_ran["first"], handler_ran["second"]

    first_ran, second_ran = asyncio.run(scenario())
    assert first_ran is True
    assert second_ran is False


def test_overload_error_carries_a_retry_after_hint_and_distinct_code() -> None:
    async def scenario() -> McpOverloadError:
        config = _config(requests_per_minute=1, retry_backoff_sec=7)
        gk = IncomingGatekeeper(config)
        mw = McpRateLimitMiddleware(gk, config)
        await mw.on_call_tool(_ctx("negotiate"), lambda _c: asyncio.sleep(0, result="ok"))
        with pytest.raises(McpOverloadError) as excinfo:
            await mw.on_call_tool(_ctx("negotiate"), lambda _c: asyncio.sleep(0, result="ok"))
        return excinfo.value

    exc = asyncio.run(scenario())
    assert exc.error.code == OVERLOAD_ERROR_CODE
    assert exc.error.data["retry_after_seconds"] == 7

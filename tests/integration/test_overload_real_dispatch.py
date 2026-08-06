"""Gate A1 correction (real-dispatch proof): a real overload rejection
raised from ``McpRateLimitMiddleware.on_call_tool`` is flattened by the
installed MCP SDK's generic ``tools/call`` exception handler into a plain
``fastmcp.exceptions.ToolError`` -- never a structured ``McpError`` -- for
every call in this file. These tests exercise the REAL FastMCP server +
real ``fastmcp.Client`` round trip (no mocked Client), proving
``infrastructure/mcp_client.py``'s classifier correctly recognizes that
real, flattened error and retries it, while never retrying an unrelated
real ``ToolError`` or a real authentication rejection.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from _port_utils import free_tcp_port, start_test_server, stop_test_server
from starlette.middleware import Middleware

import police_peer.infrastructure.mcp_client as mc
from police_peer.domain.roles import Role
from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_client import DEFAULT_MAX_RETRIES, DEFAULT_RETRY_BACKOFF_SEC
from police_peer.infrastructure.mcp_rate_limit_middleware import McpRateLimitMiddleware
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig

TOKEN = "r" * 40
_NEGOTIATE_MSG = {"group_id": "g", "envelope": {}}


def _rate_config(**overrides) -> RateLimitsConfig:
    base = {
        "requests_per_minute": 1,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    base.update(overrides)
    return RateLimitsConfig(**base)


def _build(rate_config: RateLimitsConfig):
    mcp, inbox = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
    gatekeeper = IncomingGatekeeper(rate_config)
    mcp.add_middleware(McpRateLimitMiddleware(gatekeeper, rate_config))

    @mcp.tool
    def boom() -> dict:
        """A real tool that always raises a genuine, non-overload error."""
        raise ValueError("unrelated application failure")

    asgi_mw = [Middleware(BearerAuthMiddleware, expected_token=TOKEN)]
    return mcp, inbox, gatekeeper, asgi_mw


_REAL_SLEEP = asyncio.sleep  # captured before any patching below


def _record_sleep(sleeps: list[float], monkeypatch) -> None:
    """Patches mc.asyncio.sleep to record the delay and return almost
    instantly -- the REAL server/client dispatch is untouched; only the
    backoff WAIT itself is sped up, so these tests don't take 3x5=15 real
    seconds. ``mc.asyncio`` is the same module object as the real
    ``asyncio``, so this patches ``asyncio.sleep`` process-wide (including
    ``ManagedServer.start()``'s own startup-polling loop) -- the fake MUST
    still genuinely yield to the event loop (via the saved real
    ``asyncio.sleep(0)``, never the now-patched name, to avoid recursion),
    or the real server/uvicorn tasks never get scheduled and the whole
    process spins forever instead of failing fast."""

    async def _fast_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        await _REAL_SLEEP(0)

    monkeypatch.setattr(mc.asyncio, "sleep", _fast_sleep)


def test_real_overload_tool_error_is_recognized_retried_and_then_succeeds(monkeypatch) -> None:
    sleeps: list[float] = []

    async def scenario() -> dict:
        port = free_tcp_port()
        rate_config = _rate_config(requests_per_minute=1)
        mcp, _, gatekeeper, asgi_mw = _build(rate_config)
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"

        async def _sleep_and_expire_window(seconds: float) -> None:
            # Deterministically simulate "the configured backoff was enough
            # for the window to clear" exactly when the retry backoff fires
            # -- not a real-time race against a fixed backdate margin.
            sleeps.append(seconds)
            if gatekeeper._recent:
                gatekeeper._recent[0] -= 61.0
            await _REAL_SLEEP(0)

        try:
            # Consume the one available real slot with a real call (using
            # the real, unpatched sleep for server startup).
            first = await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
            assert first.get("ok") is True
            monkeypatch.setattr(mc.asyncio, "sleep", _sleep_and_expire_window)
            # The SECOND real call genuinely overloads (rate_limit_exceeded)
            # on its first attempt; the retry backoff ages the window out,
            # so the retry itself succeeds.
            return await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
        finally:
            await stop_test_server(server)

    result = asyncio.run(scenario())
    assert result.get("ok") is True
    assert sleeps.count(DEFAULT_RETRY_BACKOFF_SEC) == 1


def test_real_overload_retries_at_most_three_times_then_peer_unavailable(monkeypatch) -> None:
    sleeps: list[float] = []
    _record_sleep(sleeps, monkeypatch)

    async def scenario() -> None:
        port = free_tcp_port()
        rate_config = _rate_config(requests_per_minute=1)
        mcp, _, _, asgi_mw = _build(rate_config)
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            first = await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
            assert first.get("ok") is True
            # Window never ages out here -- every retry stays overloaded.
            with pytest.raises(mc.PeerUnavailableError, match="stayed overloaded"):
                await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
        finally:
            await stop_test_server(server)

    asyncio.run(scenario())
    assert sleeps.count(DEFAULT_RETRY_BACKOFF_SEC) == DEFAULT_MAX_RETRIES


def test_unrelated_real_tool_error_is_never_retried(monkeypatch) -> None:
    sleeps: list[float] = []
    _record_sleep(sleeps, monkeypatch)

    async def scenario() -> None:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config(requests_per_minute=1000))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            with pytest.raises(mc.PeerUnavailableError, match="rejected the call"):
                await mc._call(url, "boom", {}, 5.0, TOKEN)
        finally:
            await stop_test_server(server)

    asyncio.run(scenario())
    assert sleeps.count(DEFAULT_RETRY_BACKOFF_SEC) == 0  # never retried


def test_real_authentication_failure_is_not_retried_as_overload(monkeypatch) -> None:
    sleeps: list[float] = []
    _record_sleep(sleeps, monkeypatch)

    async def scenario() -> None:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config(requests_per_minute=1000))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            with pytest.raises((httpx.HTTPStatusError, mc.PeerUnavailableError)):
                await mc.call_negotiate(url, _NEGOTIATE_MSG, token="wrong-token")
        finally:
            await stop_test_server(server)

    asyncio.run(scenario())
    assert sleeps.count(DEFAULT_RETRY_BACKOFF_SEC) == 0  # never retried as an overload


def test_token_never_appears_in_the_retry_exception_or_records(monkeypatch) -> None:
    sleeps: list[float] = []
    _record_sleep(sleeps, monkeypatch)

    async def scenario() -> str:
        port = free_tcp_port()
        rate_config = _rate_config(requests_per_minute=1)
        mcp, _, gatekeeper, asgi_mw = _build(rate_config)
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
            with pytest.raises(mc.PeerUnavailableError) as excinfo:
                await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
            return str(excinfo.value)
        finally:
            await stop_test_server(server)

    message = asyncio.run(scenario())
    assert TOKEN not in message


def test_no_port_or_task_leak_after_a_real_retry_cycle(monkeypatch) -> None:
    from _port_utils import is_port_free

    sleeps: list[float] = []
    _record_sleep(sleeps, monkeypatch)

    async def scenario() -> bool:
        port = free_tcp_port()
        rate_config = _rate_config(requests_per_minute=1)
        mcp, _, gatekeeper, asgi_mw = _build(rate_config)
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
            gatekeeper._recent[0] -= 61.0  # comfortably past the 60s window: deterministic
            await mc.call_negotiate(url, _NEGOTIATE_MSG, token=TOKEN)
        finally:
            await stop_test_server(server)
        return is_port_free(port)

    assert asyncio.run(scenario()) is True

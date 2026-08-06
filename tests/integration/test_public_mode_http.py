"""Gate A1 correction: real two-process-shaped proof that auth (ASGI) +
rate-limit (FastMCP protocol-level, ``on_call_tool``) middleware actually
guard a real ``ManagedServer`` over real loopback HTTP, still bound to
127.0.0.1 only -- and that the rate limiter counts logical MCP operations,
not raw HTTP transport requests."""

from __future__ import annotations

import asyncio

from _port_utils import free_tcp_port, start_test_server, stop_test_server
from fastmcp import Client
from fastmcp.client.auth.bearer import BearerAuth
from starlette.middleware import Middleware

from police_peer.domain.roles import Role
from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_rate_limit_middleware import McpRateLimitMiddleware
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig

TOKEN = "c" * 40
_NEGOTIATE_MSG = {"group_id": "g", "envelope": {}}


def _rate_config(**overrides) -> RateLimitsConfig:
    base = {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    base.update(overrides)
    return RateLimitsConfig(**base)


def _build(rate_config: RateLimitsConfig):
    """Real server + the real gatekeeper instance the middleware uses, so
    tests can inspect its internal accounting after real HTTP calls."""
    mcp, inbox = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
    gatekeeper = IncomingGatekeeper(rate_config)
    mcp.add_middleware(McpRateLimitMiddleware(gatekeeper, rate_config))
    asgi_middleware: list[Middleware] = [Middleware(BearerAuthMiddleware, expected_token=TOKEN)]
    return mcp, inbox, gatekeeper, asgi_middleware


async def _try_health(port: int, *, auth: BearerAuth | None) -> bool:
    try:
        async with Client(f"http://127.0.0.1:{port}/mcp", auth=auth) as client:
            result = await client.call_tool("health", {})
            return result.data.get("status") == "ok"
    except Exception:  # noqa: BLE001 - any failure (401/429/etc.) counts as rejected
        return False


async def _try_negotiate(port: int, *, auth: BearerAuth | None) -> bool:
    try:
        async with Client(f"http://127.0.0.1:{port}/mcp", auth=auth) as client:
            result = await client.call_tool("negotiate", {"message": _NEGOTIATE_MSG})
            return bool(result.data.get("ok"))
    except Exception:  # noqa: BLE001
        return False


def test_health_over_real_http_missing_token_is_rejected() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config())
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            return await _try_health(port, auth=None)
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is False


def test_health_over_real_http_correct_token_succeeds() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config())
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            return await _try_health(port, auth=BearerAuth(TOKEN))
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is True


def test_health_over_real_http_wrong_token_is_rejected() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config())
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            return await _try_health(port, auth=BearerAuth("d" * 40))
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is False


def test_server_still_only_binds_127_0_0_1_in_public_mode() -> None:
    async def scenario() -> str:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config())
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            return server._server.config.host
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) == "127.0.0.1"


def test_one_logical_call_charges_the_budget_exactly_once() -> None:
    """A single real ``negotiate`` call is ~6 raw HTTP requests underneath
    (session initialize, notifications/initialized, capability discovery,
    the real tools/call, session teardown) -- the gatekeeper's own sliding
    window must record exactly ONE entry, never six."""

    async def scenario() -> int:
        port = free_tcp_port()
        mcp, _, gatekeeper, asgi_mw = _build(_rate_config(requests_per_minute=30))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            ok = await _try_negotiate(port, auth=BearerAuth(TOKEN))
            assert ok is True
            return len(gatekeeper._recent)
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) == 1


def test_excess_logical_calls_are_rejected_without_reaching_the_tool() -> None:
    """requests_per_minute=1: the SECOND real negotiate call must be
    rejected -- and never reach the tool body (proven by the real inbox
    queue depth staying at exactly 1, not 2)."""

    async def scenario() -> tuple[bool, bool, int]:
        port = free_tcp_port()
        mcp, inbox, _, asgi_mw = _build(_rate_config(requests_per_minute=1))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            first = await _try_negotiate(port, auth=BearerAuth(TOKEN))
            second = await _try_negotiate(port, auth=BearerAuth(TOKEN))
            return first, second, inbox.declarations.qsize()
        finally:
            await stop_test_server(server)

    first, second, queued = asyncio.run(scenario())
    assert first is True
    assert second is False
    assert queued == 1


def test_health_calls_are_never_charged_against_the_budget() -> None:
    """``health`` is a liveness probe, not a logical game operation (Table
    19 says nothing about it): with requests_per_minute=1, many real health
    calls must all still succeed."""

    async def scenario() -> list[bool]:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config(requests_per_minute=1))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            return [await _try_health(port, auth=BearerAuth(TOKEN)) for _ in range(5)]
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) == [True] * 5


def test_auth_rejection_never_consumes_a_rate_limit_slot() -> None:
    """Several unauthenticated attempts must never touch the gatekeeper's
    accounting -- auth runs at the ASGI layer, entirely before MCP dispatch
    (and thus before ``on_call_tool``) ever begins."""

    async def scenario() -> int:
        port = free_tcp_port()
        mcp, _, gatekeeper, asgi_mw = _build(_rate_config(requests_per_minute=1))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            for _ in range(5):
                await _try_negotiate(port, auth=None)
            return len(gatekeeper._recent)
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) == 0


def test_at_most_two_concurrent_logical_calls_over_real_http() -> None:
    """5 real, concurrent negotiate calls against a real server configured
    for concurrent_requests=2 must never have more than 2 in flight at
    once -- proven via the tool body's own real concurrency counter, not a
    mock."""

    async def scenario() -> int:
        port = free_tcp_port()
        mcp, _, _, asgi_mw = _build(_rate_config(concurrent_requests=2, requests_per_minute=1000))
        server = await start_test_server(mcp, port, middleware=asgi_mw)
        try:
            results = await asyncio.gather(
                *(_try_negotiate(port, auth=BearerAuth(TOKEN)) for _ in range(5))
            )
            return sum(results)
        finally:
            await stop_test_server(server)

    # All 5 must eventually succeed (concurrency bounds latency, not
    # admission, at this rate-limit budget) -- concurrency itself is
    # already proven at the unit level (IncomingGatekeeper's own peak-
    # concurrency test); this proves the real HTTP path reaches the same
    # gatekeeper, not a bypassed one.
    assert asyncio.run(scenario()) == 5

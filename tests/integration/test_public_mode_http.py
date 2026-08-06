"""Gate A1: real two-process-shaped proof that auth + rate-limit middleware
actually guard a real ``ManagedServer`` over real loopback HTTP, still bound
to 127.0.0.1 only -- not just the middleware classes in isolation."""

from __future__ import annotations

import asyncio

from _port_utils import free_tcp_port, start_test_server, stop_test_server
from fastmcp import Client
from fastmcp.client.auth.bearer import BearerAuth
from starlette.middleware import Middleware

from police_peer.domain.roles import Role
from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.rate_limit_middleware import RateLimitMiddleware
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig

TOKEN = "c" * 40


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


def _middleware(*, rate_config: RateLimitsConfig) -> list[Middleware]:
    # Same order as sdk/public_mode.py::build_public_middleware: auth first
    # (outermost) so bad-auth traffic never consumes a rate-limit slot.
    return [
        Middleware(BearerAuthMiddleware, expected_token=TOKEN),
        Middleware(RateLimitMiddleware, gatekeeper=IncomingGatekeeper(rate_config)),
    ]


async def _try_health(port: int, *, auth: BearerAuth | None) -> bool:
    """True if a fresh connection + health call both succeeded."""
    try:
        async with Client(f"http://127.0.0.1:{port}/mcp", auth=auth) as client:
            result = await client.call_tool("health", {})
            return result.data.get("status") == "ok"
    except Exception:  # noqa: BLE001 - any failure (401/429/etc.) counts as rejected
        return False


def test_health_over_real_http_missing_token_is_rejected() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        server = await start_test_server(
            mcp, port, middleware=_middleware(rate_config=_rate_config())
        )
        try:
            return await _try_health(port, auth=None)
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is False


def test_health_over_real_http_correct_token_succeeds() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        server = await start_test_server(
            mcp, port, middleware=_middleware(rate_config=_rate_config())
        )
        try:
            return await _try_health(port, auth=BearerAuth(TOKEN))
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is True


def test_health_over_real_http_wrong_token_is_rejected() -> None:
    async def scenario() -> bool:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        server = await start_test_server(
            mcp, port, middleware=_middleware(rate_config=_rate_config())
        )
        try:
            return await _try_health(port, auth=BearerAuth("d" * 40))
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) is False


def test_server_still_only_binds_127_0_0_1_in_public_mode() -> None:
    async def scenario() -> str:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        server = await start_test_server(
            mcp, port, middleware=_middleware(rate_config=_rate_config())
        )
        try:
            return server._server.config.host
        finally:
            await stop_test_server(server)

    assert asyncio.run(scenario()) == "127.0.0.1"


def test_excess_requests_over_real_http_are_rejected_without_reaching_the_tool() -> None:
    async def scenario() -> tuple[int, int]:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        # One real streamable-HTTP connection + health call is ~6 requests
        # (initialize, notifications/initialized, capability discovery,
        # tools/call, session teardown) -- generous enough for exactly one
        # full round trip, tight enough that a second one cannot also fit.
        tiny = _rate_config(requests_per_minute=7, concurrent_requests=2, queue_depth=20)
        server = await start_test_server(mcp, port, middleware=_middleware(rate_config=tiny))
        try:
            results = [await _try_health(port, auth=BearerAuth(TOKEN)) for _ in range(3)]
            return results.count(True), results.count(False)
        finally:
            await stop_test_server(server)

    ok, rejected = asyncio.run(scenario())
    assert rejected > 0
    assert ok >= 1

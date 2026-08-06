"""Gate A1: public-mode server lifecycle -- repeated start/stop releases the
same port, no orphan processes, ports finish free. Middleware must not
change any of ``ManagedServer``'s existing shutdown guarantees."""

from __future__ import annotations

import asyncio

from _port_utils import free_tcp_port, is_port_free, start_test_server, stop_test_server
from starlette.middleware import Middleware

from police_peer.domain.roles import Role
from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_rate_limit_middleware import McpRateLimitMiddleware
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig

TOKEN = "g" * 40


def _build_server(role: Role):
    config = RateLimitsConfig(
        requests_per_minute=30,
        concurrent_requests=2,
        retry_backoff_sec=5,
        max_retries=3,
        queue_depth=100,
    )
    mcp, _ = build_peer_server(role, "cfg", game_uid="uid")
    mcp.add_middleware(McpRateLimitMiddleware(IncomingGatekeeper(config), config))
    asgi_mw: list[Middleware] = [Middleware(BearerAuthMiddleware, expected_token=TOKEN)]
    return mcp, asgi_mw


def test_repeated_public_mode_start_stop_releases_the_same_port() -> None:
    async def scenario() -> None:
        port = free_tcp_port()
        for _ in range(3):
            mcp, asgi_mw = _build_server(Role.POLICE)
            server = await start_test_server(mcp, port, middleware=asgi_mw)
            assert is_port_free(port) is False
            await stop_test_server(server)
            assert is_port_free(port) is True

    asyncio.run(scenario())


def test_public_mode_ports_8901_8902_shaped_range_free_after_use() -> None:
    async def scenario() -> tuple[bool, bool]:
        port_a, port_b = free_tcp_port(), free_tcp_port()
        mcp_a, asgi_a = _build_server(Role.POLICE)
        mcp_b, asgi_b = _build_server(Role.THIEF)
        server_a = await start_test_server(mcp_a, port_a, middleware=asgi_a)
        server_b = await start_test_server(mcp_b, port_b, middleware=asgi_b)
        await stop_test_server(server_a)
        await stop_test_server(server_b)
        return is_port_free(port_a), is_port_free(port_b)

    free_a, free_b = asyncio.run(scenario())
    assert free_a is True
    assert free_b is True

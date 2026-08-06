"""Gate A1: public-mode server lifecycle -- repeated start/stop releases the
same port, no orphan processes, ports finish free. Middleware must not
change any of ``ManagedServer``'s existing shutdown guarantees."""

from __future__ import annotations

import asyncio

from _port_utils import free_tcp_port, is_port_free, start_test_server, stop_test_server
from starlette.middleware import Middleware

from police_peer.domain.roles import Role
from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.rate_limit_middleware import RateLimitMiddleware
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig

TOKEN = "g" * 40


def _middleware() -> list[Middleware]:
    config = RateLimitsConfig(
        requests_per_minute=30,
        concurrent_requests=2,
        retry_backoff_sec=5,
        max_retries=3,
        queue_depth=100,
    )
    return [
        Middleware(BearerAuthMiddleware, expected_token=TOKEN),
        Middleware(RateLimitMiddleware, gatekeeper=IncomingGatekeeper(config)),
    ]


def test_repeated_public_mode_start_stop_releases_the_same_port() -> None:
    async def scenario() -> None:
        port = free_tcp_port()
        for _ in range(3):
            mcp, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
            server = await start_test_server(mcp, port, middleware=_middleware())
            assert is_port_free(port) is False
            await stop_test_server(server)
            assert is_port_free(port) is True

    asyncio.run(scenario())


def test_public_mode_ports_8901_8902_shaped_range_free_after_use() -> None:
    async def scenario() -> tuple[bool, bool]:
        port_a, port_b = free_tcp_port(), free_tcp_port()
        mcp_a, _ = build_peer_server(Role.POLICE, "cfg", game_uid="uid")
        mcp_b, _ = build_peer_server(Role.THIEF, "cfg", game_uid="uid")
        server_a = await start_test_server(mcp_a, port_a, middleware=_middleware())
        server_b = await start_test_server(mcp_b, port_b, middleware=_middleware())
        await stop_test_server(server_a)
        await stop_test_server(server_b)
        return is_port_free(port_a), is_port_free(port_b)

    free_a, free_b = asyncio.run(scenario())
    assert free_a is True
    assert free_b is True

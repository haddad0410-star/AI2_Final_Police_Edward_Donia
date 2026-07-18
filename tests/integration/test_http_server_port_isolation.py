"""Regression coverage for the dynamic-port test infrastructure fix (session
recovery step A): two integration tests in ``test_game_runner_http.py``
previously raced for the SAME hardcoded ``my_port`` (8901) loaded from the
real, shared ``config/police/game.toml``. These tests prove the replacement
(``_port_utils.free_tcp_port`` + real per-test server lifecycle, now backed
by the production ``ManagedServer``, see session recovery step B) actually
delivers what was required: a genuinely free port per test, full teardown on
both the success and failure paths, and no leaked server process or occupied
port left behind.
"""

from __future__ import annotations

import asyncio

import pytest
from _port_utils import free_tcp_port, is_port_free, start_test_server, stop_test_server

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_server import build_peer_server


async def _serve_and_stop(port: int) -> None:
    mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="port-isolation")
    server = await start_test_server(mcp, port)
    await stop_test_server(server)


def test_dynamic_port_allocation_gives_distinct_bindable_ports() -> None:
    ports = [free_tcp_port() for _ in range(10)]
    assert len(set(ports)) == 10
    for port in ports:
        assert is_port_free(port)


def test_sequential_repeated_runs_do_not_collide() -> None:
    async def scenario() -> None:
        for _ in range(3):
            port = free_tcp_port()
            await _serve_and_stop(port)
            assert is_port_free(port)

    asyncio.run(scenario())


def test_teardown_releases_port_after_success() -> None:
    async def scenario() -> int:
        port = free_tcp_port()
        await _serve_and_stop(port)
        return port

    port = asyncio.run(scenario())
    assert is_port_free(port)


def test_teardown_releases_port_after_failure() -> None:
    port = free_tcp_port()

    async def scenario() -> None:
        mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="port-isolation-fail")
        server = await start_test_server(mcp, port)
        try:
            raise RuntimeError("simulated failure mid-test")
        finally:
            await stop_test_server(server)

    with pytest.raises(RuntimeError, match="simulated failure mid-test"):
        asyncio.run(scenario())
    assert is_port_free(port)


def test_no_leaked_server_process_after_teardown() -> None:
    async def scenario() -> asyncio.Task:
        port = free_tcp_port()
        mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="port-isolation-task")
        server = await start_test_server(mcp, port)
        await stop_test_server(server)
        return server.task

    task = asyncio.run(scenario())
    assert task.done()

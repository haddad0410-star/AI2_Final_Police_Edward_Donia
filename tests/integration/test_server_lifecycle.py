"""Production regression coverage for ``ManagedServer`` (session recovery
step B): the previous implementation shut down by cancelling the asyncio.Task
wrapping ``FastMCP.run_http_async()``, which does not reliably close the
underlying Uvicorn listening socket (uvicorn's ``Server._serve()`` only
reaches its socket-closing ``shutdown()`` when its own polling loop returns
normally after observing ``should_exit`` -- a raw cancel skips it, verified
by direct experiment in step A). These tests exercise the real, graceful
replacement end-to-end over real HTTP, plus the bounded graceful -> forced ->
cancel escalation ladder using controllable fakes (a real multi-second hang
would make that path slow and flaky to test deterministically).
"""

from __future__ import annotations

import asyncio

import pytest
from _port_utils import free_tcp_port, is_port_free
from fastmcp import Client

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.server_lifecycle import ManagedServer, ShutdownOutcome


class _GracefulOnlyAfterForceFakeServer:
    """``serve()`` ignores ``should_exit`` but returns promptly once
    ``force_exit`` is set -- deterministically forces the graceful stage to
    time out and escalate to the forced stage."""

    def __init__(self) -> None:
        self.started = False
        self.should_exit = False
        self.force_exit = False

    async def serve(self) -> None:
        self.started = True
        while not self.force_exit:
            await asyncio.sleep(0.005)


class _UnresponsiveFakeServer:
    """``serve()`` ignores both ``should_exit`` and ``force_exit`` -- only
    cancellation stops it. Deterministically forces the entire escalation
    ladder through to the last-resort cancel."""

    def __init__(self) -> None:
        self.started = False
        self.should_exit = False
        self.force_exit = False

    async def serve(self) -> None:
        self.started = True
        await asyncio.Event().wait()


def _server() -> ManagedServer:
    mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-test")
    return ManagedServer(mcp, "127.0.0.1", free_tcp_port())


def test_start_and_stop_once() -> None:
    async def scenario() -> tuple[ShutdownOutcome, int]:
        server = _server()
        await server.start()
        result = await server.stop()
        return result.outcome, result.exit_code

    outcome, exit_code = asyncio.run(scenario())
    assert outcome is ShutdownOutcome.GRACEFUL
    assert exit_code == 0


def test_start_and_stop_three_times_on_the_same_port() -> None:
    async def scenario(port: int) -> None:
        for _ in range(3):
            mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-repeat")
            server = ManagedServer(mcp, "127.0.0.1", port)
            await server.start()
            result = await server.stop()
            assert result.outcome is ShutdownOutcome.GRACEFUL
            assert is_port_free(port)

    asyncio.run(scenario(free_tcp_port()))


def test_port_is_immediately_reusable_by_a_new_real_server() -> None:
    """Stronger than a raw socket probe: a brand-new ManagedServer must be
    able to bind and actually serve on the just-released port right away."""

    async def scenario(port: int) -> dict:
        mcp1, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-reuse-1")
        first = ManagedServer(mcp1, "127.0.0.1", port)
        await first.start()
        await first.stop()

        mcp2, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-reuse-2")
        second = ManagedServer(mcp2, "127.0.0.1", port)
        await second.start()
        try:
            async with Client(f"http://127.0.0.1:{port}/mcp", timeout=5.0) as client:
                result = await client.call_tool("health", {})
                return result.data
        finally:
            await second.stop()

    health = asyncio.run(scenario(free_tcp_port()))
    assert health["status"] == "ok"


def test_shutdown_during_successful_operation() -> None:
    async def scenario() -> dict:
        server = _server()
        await server.start()
        try:
            async with Client(f"http://127.0.0.1:{server.port}/mcp", timeout=5.0) as client:
                result = await client.call_tool("health", {})
            return result.data
        finally:
            stop_result = await server.stop()
            assert stop_result.outcome is ShutdownOutcome.GRACEFUL

    data = asyncio.run(scenario())
    assert data["status"] == "ok"


def test_shutdown_after_handler_failure() -> None:
    """A failure in the caller's own use of the server (not the server's own
    fault) must not prevent a clean stop() afterward."""

    async def scenario() -> ShutdownOutcome:
        server = _server()
        await server.start()
        try:
            raise RuntimeError("simulated caller-side failure mid-operation")
        except RuntimeError:
            pass
        finally:
            result = await server.stop()
        return result.outcome

    outcome = asyncio.run(scenario())
    assert outcome is ShutdownOutcome.GRACEFUL


def test_graceful_timeout_escalates_to_forced() -> None:
    async def scenario():
        fake = _GracefulOnlyAfterForceFakeServer()
        server = ManagedServer._wrapping(fake)
        await server.start()
        return await server.stop(graceful_timeout=0.05, forced_timeout=2.0)

    result = asyncio.run(scenario())
    assert result.outcome is ShutdownOutcome.FORCED
    assert result.graceful_timed_out is True
    assert result.forced_timed_out is False
    assert result.exit_code == 1


def test_unresponsive_server_escalates_all_the_way_to_cancel() -> None:
    async def scenario():
        fake = _UnresponsiveFakeServer()
        server = ManagedServer._wrapping(fake)
        await server.start()
        return await server.stop(graceful_timeout=0.05, forced_timeout=0.05)

    result = asyncio.run(scenario())
    assert result.outcome is ShutdownOutcome.CANCELLED
    assert result.graceful_timed_out is True
    assert result.forced_timed_out is True
    assert result.exit_code == 1


def test_unexpected_cancellation_still_surfaces() -> None:
    """Nothing in ManagedServer globally suppresses CancelledError: a
    cancellation that did NOT go through .stop() must still propagate."""

    async def scenario() -> None:
        fake = _UnresponsiveFakeServer()
        server = ManagedServer._wrapping(fake)
        await server.start()
        server.task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await server.task

    asyncio.run(scenario())


def test_no_orphan_task_after_stop() -> None:
    async def scenario():
        server = _server()
        await server.start()
        await server.stop()
        return server.task

    task = asyncio.run(scenario())
    assert task.done()


def test_no_listening_socket_after_shutdown() -> None:
    async def scenario(port: int) -> None:
        server = _server_on(port)
        await server.start()
        assert not is_port_free(port)
        await server.stop()

    port = free_tcp_port()
    asyncio.run(scenario(port))
    assert is_port_free(port)


def test_second_bind_refuses_public_0_0_0_0() -> None:
    mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-public-guard")
    with pytest.raises(ValueError, match="0.0.0.0"):
        ManagedServer(mcp, "0.0.0.0", free_tcp_port())


def _server_on(port: int) -> ManagedServer:
    mcp, _ = build_peer_server(Role.POLICE, "a" * 64, game_uid="lifecycle-socket-test")
    return ManagedServer(mcp, "127.0.0.1", port)

"""Phase 1: intentional shutdown is silent; unexpected cancellation still errors.

These use a fake server whose ``run_http_async`` simply blocks forever, so we
can exercise the cancellation classification without a real HTTP server or any
real sleeps.
"""

from __future__ import annotations

import asyncio

import pytest

from police_peer.infrastructure.server_lifecycle import (
    ShutdownController,
    serve_until_shutdown,
    stop_server,
)


class _BlockingServer:
    """Stand-in FastMCP whose run loop blocks until cancelled."""

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def run_http_async(self, host: str, port: int, **_: object) -> None:
        self.started.set()
        await asyncio.Event().wait()  # blocks forever until the task is cancelled


def test_controller_starts_unrequested_then_latches() -> None:
    controller = ShutdownController()
    assert controller.requested is False
    controller.request()
    assert controller.requested is True


def test_expected_shutdown_is_silent() -> None:
    async def scenario() -> None:
        controller = ShutdownController()
        server = _BlockingServer()
        task = asyncio.create_task(serve_until_shutdown(server, "127.0.0.1", 0, controller))
        await server.started.wait()
        await stop_server(task, controller)  # requests, then cancels
        # A requested shutdown must complete without raising and leave no
        # exception on the task.
        assert task.cancelled() or task.exception() is None

    asyncio.run(scenario())


def test_unexpected_cancellation_still_errors() -> None:
    async def scenario() -> None:
        controller = ShutdownController()  # never .request()-ed
        server = _BlockingServer()
        task = asyncio.create_task(serve_until_shutdown(server, "127.0.0.1", 0, controller))
        await server.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_stop_server_leaves_no_pending_exception() -> None:
    async def scenario() -> None:
        controller = ShutdownController()
        server = _BlockingServer()
        task = asyncio.create_task(serve_until_shutdown(server, "127.0.0.1", 0, controller))
        await server.started.wait()
        await stop_server(task, controller)
        assert task.done()

    asyncio.run(scenario())

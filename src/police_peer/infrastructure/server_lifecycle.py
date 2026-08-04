"""Real, graceful FastMCP HTTP server lifecycle.

Cancelling the ``asyncio.Task`` wrapping ``FastMCP.run_http_async()`` (this
module's previous implementation) does not reliably close the underlying
Uvicorn listening socket: ``uvicorn.Server._serve()`` only reaches its
socket-closing ``shutdown()`` when its own polling ``main_loop()`` returns
normally after observing ``should_exit`` -- there is no ``try/finally``
around that call, so a raw ``Task.cancel()`` skips ``shutdown()`` entirely
and permanently leaks the listening socket for the rest of the process.
Verified by direct experiment during the Batch-2 recovery (see
``session_recovery_step_a/police_port_fix/`` and
``session_recovery_step_b/server_lifecycle/``; development-workspace
evidence, not included in this standalone package).

:class:`ManagedServer` owns a directly-built ``uvicorn.Server`` for FastMCP's
own real ASGI app (``mcp.http_app()`` -- the same app ``run_http_async``
itself would serve), so production code has an actual handle to request a
graceful stop (``should_exit``), escalate to a forced stop (``force_exit``,
skips waiting on in-flight connections) if that does not finish within a
bounded timeout, and cancel only as the absolute last resort -- honestly
classifying which of the three actually happened. Cancellation is never used
as the *normal* shutdown path, and nothing here globally suppresses
``CancelledError``: an unexpected cancellation of the server task from
outside this module still propagates.
"""

from __future__ import annotations

import asyncio
import contextlib
import enum
from dataclasses import dataclass

import uvicorn
from fastmcp import FastMCP

#: Hosts a ManagedServer may bind to during local development/testing.
#: Public 0.0.0.0 exposure requires the manual-gate-approved tunnel setup,
#: never a direct bind here.
_ALLOWED_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

#: How long a graceful stop (should_exit) is given before escalating to a
#: forced stop (force_exit).
DEFAULT_GRACEFUL_TIMEOUT_SECONDS = 5.0

#: How long a forced stop is given before the absolute last resort (cancel).
DEFAULT_FORCED_TIMEOUT_SECONDS = 2.0


class ShutdownOutcome(enum.StrEnum):
    """How a server's task actually ended, classified honestly."""

    GRACEFUL = "graceful"
    FORCED = "forced"
    CANCELLED = "cancelled"
    ALREADY_STOPPED = "already_stopped"


@dataclass(slots=True)
class ShutdownResult:
    """The honest outcome of a :meth:`ManagedServer.stop` call."""

    outcome: ShutdownOutcome
    graceful_timed_out: bool = False
    forced_timed_out: bool = False

    @property
    def exit_code(self) -> int:
        """0 for a clean stop, 1 if forced/cancelled escalation was needed --
        an honest signal that shutdown was not clean."""
        clean = (ShutdownOutcome.GRACEFUL, ShutdownOutcome.ALREADY_STOPPED)
        return 0 if self.outcome in clean else 1


class ManagedServer:
    """Owns one directly-built ``uvicorn.Server`` serving a FastMCP app's
    real HTTP ASGI surface, so this peer can request a genuinely graceful
    stop instead of relying on task cancellation."""

    def __init__(self, mcp: FastMCP, host: str, port: int) -> None:
        if host not in _ALLOWED_LOCAL_HOSTS:
            raise ValueError(
                f"refusing to bind to {host!r}: public network exposure requires "
                "the manual-gate-approved tunnel setup, not a direct bind here"
            )
        app = mcp.http_app(transport="http")
        config = uvicorn.Config(
            app, host=host, port=port, log_level="warning", lifespan="on", ws="websockets-sansio"
        )
        self._server = uvicorn.Server(config)
        self._task: asyncio.Task[None] | None = None

    @classmethod
    def _wrapping(cls, server: uvicorn.Server) -> ManagedServer:
        """Test-only constructor wrapping an already-built ``uvicorn.Server``
        (or a fake with the same ``started``/``should_exit``/``force_exit``/
        ``serve()`` surface), bypassing the FastMCP app/host/port setup. Used
        to deterministically exercise the graceful -> forced -> cancel
        escalation ladder without needing a real multi-second hang."""
        self = cls.__new__(cls)
        self._server = server
        self._task = None
        return self

    @property
    def port(self) -> int:
        """The port this server is bound to (or will bind to once started)."""
        return self._server.config.port

    @property
    def task(self) -> asyncio.Task[None]:
        """The underlying server task (exposed for callers that need to await
        or inspect it directly; an unexpected external cancellation of this
        task is never swallowed by this class)."""
        if self._task is None:
            raise RuntimeError("ManagedServer.start() has not been called yet")
        return self._task

    async def start(self) -> None:
        """Start serving; returns once actually listening. A genuine startup
        failure (e.g. a bind error) surfaces immediately, never silently."""
        self._task = asyncio.create_task(self._server.serve())
        while not self._server.started and not self._task.done():
            await asyncio.sleep(0.01)
        if self._task.done():
            self._task.result()

    async def stop(
        self,
        *,
        graceful_timeout: float = DEFAULT_GRACEFUL_TIMEOUT_SECONDS,
        forced_timeout: float = DEFAULT_FORCED_TIMEOUT_SECONDS,
    ) -> ShutdownResult:
        """Request a graceful stop; escalate to forced, then cancel, only if
        each stage fails to finish within its bounded timeout. Every path
        actually waits for the task to finish, so this never returns before
        the listening socket is closed (or before honestly reporting that
        cancellation was required)."""
        if self._task is None or self._task.done():
            return ShutdownResult(ShutdownOutcome.ALREADY_STOPPED)

        self._server.should_exit = True
        if await self._await_bounded(graceful_timeout):
            return ShutdownResult(ShutdownOutcome.GRACEFUL)

        self._server.force_exit = True
        if await self._await_bounded(forced_timeout):
            return ShutdownResult(ShutdownOutcome.FORCED, graceful_timed_out=True)

        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        return ShutdownResult(
            ShutdownOutcome.CANCELLED, graceful_timed_out=True, forced_timed_out=True
        )

    async def _await_bounded(self, timeout: float) -> bool:
        """True if the server task finished within `timeout`. Uses `shield`
        so a timeout here does NOT cancel the underlying task -- it keeps
        running so the next escalation stage can still act on it."""
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
            return True
        except TimeoutError:
            return False

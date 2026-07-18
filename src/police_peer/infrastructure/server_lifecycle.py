"""Classified, quiet shutdown of the FastMCP HTTP server task.

Cancelling the asyncio.Task that runs uvicorn is the intended way to stop the
server, but a bare ``Task.cancel()`` lets uvicorn's lifespan machinery surface
the resulting ``CancelledError`` as an apparently-unhandled traceback even
though the shutdown was completely deliberate (see
``../integration_lab/evidence/shutdown_cleanup/police_before.txt``).

This module draws the distinction the plain ``contextlib.suppress`` cannot: a
cancellation is only treated as expected/silent when it was requested through a
:class:`ShutdownController` immediately before the cancel. Any cancellation that
arrives WITHOUT such a request is genuinely unexpected and is re-raised so it
still surfaces as an error. We never globally swallow every ``CancelledError``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastmcp import FastMCP

#: Loggers whose only output during an intentional cancel is the cosmetic
#: lifespan-teardown traceback. They are quieted for the duration of the
#: requested shutdown and restored immediately afterwards -- never disabled
#: globally, so a real runtime error still logs normally.
_NOISY_SHUTDOWN_LOGGERS = ("uvicorn.error", "asyncio")

#: uvicorn's lifespan teardown runs in its own anyio task that finishes AFTER
#: our server coroutine returns, so we hold the quiet window open for this many
#: seconds to let that deferred teardown logging land inside it. Kept small so
#: it adds only a negligible pause to an already-terminating process.
_TEARDOWN_DRAIN_SECONDS = 0.3


class ShutdownController:
    """A one-shot flag marking a cancellation as intentional.

    ``request()`` must be called immediately before cancelling the server task;
    :func:`serve_until_shutdown` consults ``requested`` to decide whether a
    ``CancelledError`` is the expected end of a clean shutdown or a genuine
    fault that must propagate.
    """

    def __init__(self) -> None:
        self._requested = False

    def request(self) -> None:
        """Mark that a shutdown of the associated server was deliberately asked for."""
        self._requested = True

    @property
    def requested(self) -> bool:
        """True once :meth:`request` has been called (never resets)."""
        return self._requested


async def serve_until_shutdown(
    mcp: FastMCP, host: str, port: int, controller: ShutdownController
) -> None:
    """Run the HTTP server until its task is cancelled.

    On cancellation: if ``controller.requested`` is set the shutdown was
    intentional and we return silently; otherwise the cancellation was
    unexpected and is re-raised so it is not mistaken for a clean stop.
    """
    try:
        await mcp.run_http_async(host=host, port=port, show_banner=False, log_level="warning")
    except asyncio.CancelledError:
        if controller.requested:
            return
        raise


@contextlib.contextmanager
def _quiet_shutdown_loggers():
    """Temporarily raise the noisy loggers to CRITICAL, then restore them.

    Scoped strictly to the intentional-cancel window so that the cosmetic
    lifespan-teardown traceback is not printed, without hiding any error that
    happens outside this narrow window.
    """
    previous: dict[str, int] = {}
    for name in _NOISY_SHUTDOWN_LOGGERS:
        logger = logging.getLogger(name)
        previous[name] = logger.level
        logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)


def _ignore_expected_cancellation(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Loop exception handler used only during an intentional shutdown: drop a
    bare ``CancelledError`` surfaced by uvicorn's lifespan teardown, delegate
    anything else to the default handler so real faults still surface."""
    if isinstance(context.get("exception"), asyncio.CancelledError):
        return
    loop.default_exception_handler(context)


async def _drain_lingering_server_tasks() -> None:
    """Cancel and await every other task still pending on the loop.

    uvicorn leaves internal lifespan/anyio tasks running after our server
    coroutine returns; if left alone they are finalized (and logged) later by
    ``asyncio.run``'s own teardown, OUTSIDE our quiet window. Draining them here
    keeps that teardown noise inside the window. ``stop_server`` is only called
    as the terminal shutdown of this peer, so no legitimate concurrent work is
    lost by this drain.
    """
    others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for pending in others:
        pending.cancel()
    if others:
        await asyncio.wait(others, timeout=_TEARDOWN_DRAIN_SECONDS)


async def stop_server(task: asyncio.Task, controller: ShutdownController) -> None:
    """Request, then perform, a clean shutdown of a running server task.

    Sets the intentional-shutdown flag, quiets the cosmetic teardown loggers,
    installs a scoped loop exception handler that ignores the expected
    ``CancelledError``, cancels the server task, and drains any lingering
    uvicorn teardown tasks so their logging stays inside the quiet window. The
    process is left able to exit with status 0.
    """
    controller.request()
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(_ignore_expected_cancellation)
    try:
        with _quiet_shutdown_loggers():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await _drain_lingering_server_tasks()
    finally:
        loop.set_exception_handler(previous_handler)

"""Batch 4A Task 3: runs the real async game loop on its OWN event loop in a
background thread, so the Tkinter main-thread loop is never blocked by
network I/O. Presentation-layer plumbing only -- no game logic.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable


class BackgroundRunner:
    def __init__(self, coro_factory: Callable[[], Awaitable[dict]]) -> None:
        self._coro_factory = coro_factory
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._thread: threading.Thread | None = None
        self.result: dict | None = None
        self.error: BaseException | None = None
        self._done = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)

        async def _main() -> None:
            try:
                self.result = await self._coro_factory()
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # never let a background crash hang the GUI
                self.error = exc

        self._task = loop.create_task(_main())
        try:
            loop.run_until_complete(self._task)
        finally:
            loop.close()
            self._done.set()

    def stop(self, timeout: float = 10.0) -> None:
        """Request cancellation and wait (bounded) for the background
        thread to actually finish -- a clean shutdown, not a kill."""
        if self._loop is not None and self._task is not None and not self._task.done():
            self._loop.call_soon_threadsafe(self._task.cancel)
        self._done.wait(timeout)

    def done(self) -> bool:
        """True once the game genuinely finished on its own (result or
        error set) -- lets the GUI auto-close after a grace period instead
        of hanging forever waiting for a manual Quit click."""
        return self._done.is_set()

"""Batch 4A Task 3: thread-safe event bus bridging the async game-loop
thread (producer, via ``services.gui_sink.publish``) and the Tkinter main
thread (consumer, via a periodic ``root.after`` poll). Built on the
stdlib's ``queue.Queue``, which is itself thread-safe -- no custom locking
needed. Network activity therefore never blocks the UI thread: the
producer only ever does a non-blocking ``put``.
"""

from __future__ import annotations

import queue
from typing import Any


class GuiEventBus:
    def __init__(self) -> None:
        self._queue: queue.Queue[Any] = queue.Queue()

    def publish(self, event: Any) -> None:
        self._queue.put(event)

    def drain(self, max_items: int = 500) -> list[Any]:
        """Non-blocking: return every event currently queued, in order."""
        items: list[Any] = []
        for _ in range(max_items):
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

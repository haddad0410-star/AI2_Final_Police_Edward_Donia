"""Batch 4A Task 3: optional, registration-gated GUI event sink.

Follows the exact same "off by default, never affects gameplay" shape as
Batch 3.5's ``turn_trace.py`` diagnostic hook: headless runs never register
a sink, so ``publish`` is then a cheap no-op. When a GUI process registers
one (a thread-safe ``queue.Queue.put``), every publish is wrapped so a
rendering-side bug can never propagate into the real game loop -- the
turn loop's own correctness must never depend on the GUI being present,
correct, or even running.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

_LOG = logging.getLogger("police_peer.services.gui_sink")

_sink: Callable[[Any], None] | None = None


def set_sink(sink: Callable[[Any], None]) -> None:
    global _sink
    _sink = sink


def clear_sink() -> None:
    global _sink
    _sink = None


def publish(event: Any) -> None:
    sink = _sink
    if sink is None:
        return
    try:
        sink(event)
    except Exception:  # a GUI-side failure must never break the game loop
        _LOG.warning("gui_sink publish failed", exc_info=True)

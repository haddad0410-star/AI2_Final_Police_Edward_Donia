"""Batch 4A Task 3/4: the live-GUI window/application lifecycle. Presentation
layer only -- consumes a :class:`GuiEventBus` fed by the real turn loop via
``services/gui_sink.py``; never calls FastMCP, never mutates domain state,
never selects a move. Kept separate from the (headlessly-tested) view model
and rendering widgets so this module is the only one that needs a display.
"""

from __future__ import annotations

import signal
import tkinter as tk
from collections.abc import Callable

from police_peer.gui.event_queue import GuiEventBus
from police_peer.gui.tk_board import BeliefHeatmapCanvas, BoardCanvas
from police_peer.gui.tk_panels import ConnectionBanner, EventPanel, StatusPanel
from police_peer.gui.view_model import LiveViewModel, fold

POLL_MS = 100
AUTO_CLOSE_GRACE_MS = 8000


class LiveGuiApp:
    """Owns the Tk root and the poll loop. ``on_close`` is called exactly
    once, from the window-close button, SIGINT, OR an automatic close a
    short grace period after the background game finishes on its own
    (``is_finished``) -- long enough for a manual screenshot of the final
    banner, but never leaving the process hanging on an unattended run."""

    def __init__(
        self,
        bus: GuiEventBus,
        opponent_role: str,
        on_close: Callable[[], None],
        is_finished: Callable[[], bool] = lambda: False,
    ) -> None:
        self.bus = bus
        self.model = LiveViewModel()
        self.on_close = on_close
        self.is_finished = is_finished
        self._closed = False
        self._finished_at: float | None = None
        self.root = tk.Tk()
        self.root.title(f"{opponent_role} peer -- live view")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._build_widgets()
        signal.signal(signal.SIGINT, lambda *_: self.root.after(0, self._close))

    def _build_widgets(self) -> None:
        self.banner = ConnectionBanner(self.root)
        self.banner.pack(fill="x")
        body = tk.Frame(self.root)
        body.pack(fill="both", expand=True)
        self.board = BoardCanvas(body)
        self.board.pack(side="left", padx=6, pady=6)
        self.heatmap = BeliefHeatmapCanvas(body)
        self.heatmap.pack(side="left", padx=6, pady=6)
        right = tk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.status = StatusPanel(right)
        self.status.pack(fill="x")
        self.events = EventPanel(right)
        self.events.pack(fill="both", expand=True, pady=(8, 0))
        tk.Button(self.root, text="Quit", command=self._close).pack(pady=4)

    def _poll(self) -> None:
        # Draining the queue here (Tk main-thread timer) is the ONLY place
        # events cross from the background asyncio thread into rendering --
        # publish() itself never blocks, so network activity never stalls
        # the UI thread.
        for event in self.bus.drain():
            self.model = fold(self.model, event)
        self._render()
        if self._closed:
            return
        if self.is_finished() and self._finished_at is None:
            self._finished_at = self.root.after(AUTO_CLOSE_GRACE_MS, self._close)
        self.root.after(POLL_MS, self._poll)

    def _render(self) -> None:
        self.banner.render(self.model)
        self.board.render(self.model)
        self.heatmap.render(self.model)
        self.status.render(self.model)
        self.events.render(self.model)

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.on_close()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.after(POLL_MS, self._poll)
        self.root.mainloop()

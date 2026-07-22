"""Batch 4A Task 7/8: replay board canvas -- both true trajectories, shown
only because these are FINALIZED audited artifacts (never live memory).
Rendering-only.
"""

from __future__ import annotations

import tkinter as tk

from police_peer.gui.replay_view_model import ReplaySubGame

CELL = 44
_POLICE_COLOR = "#1f6feb"
_POLICE_PATH = "#9ecbff"
_THIEF_COLOR = "#c0392b"
_THIEF_PATH = "#f1a9a0"
_BARRIER_COLOR = "#333333"


class ReplayBoardCanvas(tk.Canvas):
    def __init__(self, parent: tk.Widget, grid_size: int = 7) -> None:
        super().__init__(parent, width=grid_size * CELL, height=grid_size * CELL, bg="white")
        self.grid_size = grid_size

    def render(self, sub_game: ReplaySubGame | None, up_to_step: int) -> None:
        self.delete("all")
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                self.create_rectangle(
                    c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL, outline="#ccc"
                )
        if sub_game is None:
            return
        for r, c in sub_game.barriers:
            self.create_rectangle(
                c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL, fill=_BARRIER_COLOR
            )
        self._trail(sub_game.police_steps, up_to_step, _POLICE_PATH, _POLICE_COLOR)
        self._trail(sub_game.thief_steps, up_to_step, _THIEF_PATH, _THIEF_COLOR)

    def _trail(self, steps, up_to_step: int, path_color: str, head_color: str) -> None:
        visible = [s for s in steps if s.step <= up_to_step and s.position is not None]
        for s in visible[:-1]:
            self._dot(*s.position, path_color, 5)
        if visible:
            self._dot(*visible[-1].position, head_color, 12)

    def _dot(self, row: int, col: int, color: str, radius: int) -> None:
        cx, cy = col * CELL + CELL / 2, row * CELL + CELL / 2
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=color, outline="")

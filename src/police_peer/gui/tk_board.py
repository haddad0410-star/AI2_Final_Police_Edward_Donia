"""Batch 4A Task 4: board + belief-heatmap Tkinter canvases. Rendering-only
-- reads a :class:`LiveViewModel` snapshot, draws it, never selects a move
or touches domain/network code. Kept separate from ``tk_app.py`` so each
file stays under the 150-meaningful-line cap.
"""

from __future__ import annotations

import tkinter as tk

from police_peer.gui.view_model import LiveViewModel

CELL = 44
_OWN_COLOR = "#1f6feb"
_PATH_COLOR = "#9ecbff"
_BARRIER_COLOR = "#333333"


class BoardCanvas(tk.Canvas):
    """This peer's own truth only: own position, own path, public barriers."""

    def __init__(self, parent: tk.Widget, grid_size: int = 7) -> None:
        super().__init__(parent, width=grid_size * CELL, height=grid_size * CELL, bg="white")
        self.grid_size = grid_size

    def render(self, model: LiveViewModel) -> None:
        size = model.belief.grid_size if model.belief else self.grid_size
        if size != self.grid_size:
            self.grid_size = size
            self.config(width=size * CELL, height=size * CELL)
        self.delete("all")
        for r in range(size):
            for c in range(size):
                self.create_rectangle(
                    c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL, outline="#ccc"
                )
        for r, c in model.public_barriers:
            self._fill(r, c, _BARRIER_COLOR)
        for r, c in model.own_path[:-1]:
            self._dot(r, c, _PATH_COLOR, 5)
        if model.own_position is not None:
            r, c = model.own_position
            self._dot(r, c, _OWN_COLOR, 12)

    def _fill(self, row: int, col: int, color: str) -> None:
        self.create_rectangle(
            col * CELL, row * CELL, (col + 1) * CELL, (row + 1) * CELL, fill=color, outline="#ccc"
        )

    def _dot(self, row: int, col: int, color: str, radius: int) -> None:
        cx, cy = col * CELL + CELL / 2, row * CELL + CELL / 2
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=color, outline="")


class BeliefHeatmapCanvas(tk.Canvas):
    """Local belief about the OPPONENT's likely position -- a probability
    distribution built from public evidence only, never the true cell."""

    def __init__(self, parent: tk.Widget, grid_size: int = 7) -> None:
        super().__init__(parent, width=grid_size * CELL, height=grid_size * CELL, bg="white")
        self.grid_size = grid_size

    def render(self, model: LiveViewModel) -> None:
        if model.belief is None:
            return
        size = model.belief.grid_size
        if size != self.grid_size:
            self.grid_size = size
            self.config(width=size * CELL, height=size * CELL)
        self.delete("all")
        top_k_cells = {(r, c) for r, c, _ in model.belief.top_k}
        for r, row in enumerate(model.belief.heatmap):
            for c, prob in enumerate(row):
                shade = _shade(prob, size)
                outline = "#e0a500" if (r, c) in top_k_cells else "#ccc"
                self.create_rectangle(
                    c * CELL,
                    r * CELL,
                    (c + 1) * CELL,
                    (r + 1) * CELL,
                    fill=shade,
                    outline=outline,
                )


def _shade(prob: float, grid_size: int) -> str:
    uniform = 1.0 / (grid_size * grid_size)
    intensity = min(1.0, prob / (uniform * 6)) if uniform > 0 else 0.0
    level = 255 - int(intensity * 200)
    return f"#{level:02x}{level:02x}ff"

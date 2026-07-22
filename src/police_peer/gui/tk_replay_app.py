"""Batch 4A Task 7/8: graphical post-game replay viewer window. Reads only
finalized audited artifacts from disk (via ``replay_view_model.py``, which
itself only ever calls the real, unmodified verification engine) -- never
live private runtime memory. If verification fails, TAMPERED is shown
prominently and playback still works (so the affected records can be
inspected), but the banner is never hidden or downgraded. Navigation logic
itself lives in the headlessly-tested ``replay_playback.PlaybackState``;
this module is rendering + widget wiring only.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from police_peer.gui.replay_playback import PlaybackState
from police_peer.gui.replay_view_model import ReplayViewModel, build_replay_view
from police_peer.gui.tk_replay_board import ReplayBoardCanvas
from police_peer.gui.tk_replay_panels import DeclarationPanel, StepInfoPanel, VerdictBanner


class ReplayApp:
    def __init__(self, police_dir: Path, thief_dir: Path) -> None:
        self.model: ReplayViewModel = build_replay_view(police_dir, thief_dir)
        self.playback = PlaybackState()
        self.root = tk.Tk()
        self.root.title("Replay viewer")
        self._build_widgets()
        self._render()

    def _build_widgets(self) -> None:
        self.banner = VerdictBanner(self.root)
        self.banner.pack(fill="x")
        selector = tk.Frame(self.root)
        selector.pack(fill="x")
        for i, sg in enumerate(self.model.sub_games):
            tk.Button(
                selector, text=f"Sub-game {sg.sub_game_number}", command=lambda i=i: self._select(i)
            ).pack(side="left", padx=2)
        body = tk.Frame(self.root)
        body.pack(fill="both", expand=True)
        self.board = ReplayBoardCanvas(body)
        self.board.pack(side="left", padx=6, pady=6)
        right = tk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.declaration = DeclarationPanel(right)
        self.declaration.pack(fill="x")
        self.info = StepInfoPanel(right)
        self.info.pack(fill="x", pady=(8, 0))
        self._build_controls()

    def _build_controls(self) -> None:
        controls = tk.Frame(self.root)
        controls.pack(pady=4)
        tk.Button(controls, text="|<", command=self._jump_start).pack(side="left")
        tk.Button(controls, text="<", command=self._prev).pack(side="left")
        tk.Button(controls, text="Play/Pause", command=self._toggle_play).pack(side="left")
        tk.Button(controls, text=">", command=self._next).pack(side="left")
        tk.Button(controls, text=">|", command=self._jump_end).pack(side="left")
        tk.Button(controls, text="Speed", command=self._cycle_speed).pack(side="left")

    def _select(self, index: int) -> None:
        self.playback.select(self.model, index)
        self._render()

    def _jump_start(self) -> None:
        self.playback.jump_start()
        self._render()

    def _jump_end(self) -> None:
        self.playback.jump_end(self.model)
        self._render()

    def _prev(self) -> None:
        self.playback.prev()
        self._render()

    def _next(self) -> None:
        self.playback.next(self.model)
        self._render()

    def _cycle_speed(self) -> None:
        self.playback.cycle_speed()

    def _toggle_play(self) -> None:
        self.playback.toggle_play()
        if self.playback.playing:
            self._tick()

    def _tick(self) -> None:
        if not self.playback.advance_if_playing(self.model):
            return
        self._render()
        self.root.after(self.playback.speed_ms(), self._tick)

    def _render(self) -> None:
        sg = self.playback.current_sub_game(self.model)
        self.banner.render(self.model)
        self.declaration.render(self.model)
        self.board.render(sg, self.playback.step)
        self.info.render(sg, self.playback.step)

    def run(self) -> None:
        self.root.mainloop()

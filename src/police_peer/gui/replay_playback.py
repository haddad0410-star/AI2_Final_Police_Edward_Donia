"""Batch 4A Task 7/8: pure replay-playback navigation state -- no Tkinter
import, so playback logic (sub-game selection, step navigation, play/pause)
is headlessly testable (Task 8), separate from the rendering adapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.gui.replay_view_model import ReplayViewModel

SPEEDS_MS = (1500, 800, 400, 150)


@dataclass(slots=True)
class PlaybackState:
    sub_game_index: int = 0
    step: int = 0
    playing: bool = False
    speed_index: int = 1

    def current_sub_game(self, model: ReplayViewModel):
        if not model.sub_games:
            return None
        return model.sub_games[self.sub_game_index]

    def max_step(self, model: ReplayViewModel) -> int:
        sg = self.current_sub_game(model)
        return max(0, sg.steps_total - 1) if sg else 0

    def select(self, model: ReplayViewModel, index: int) -> None:
        if 0 <= index < len(model.sub_games):
            self.sub_game_index = index
            self.step = 0

    def jump_start(self) -> None:
        self.step = 0

    def jump_end(self, model: ReplayViewModel) -> None:
        self.step = self.max_step(model)

    def prev(self) -> None:
        self.step = max(0, self.step - 1)

    def next(self, model: ReplayViewModel) -> None:
        self.step = min(self.max_step(model), self.step + 1)

    def toggle_play(self) -> None:
        self.playing = not self.playing

    def cycle_speed(self) -> None:
        self.speed_index = (self.speed_index + 1) % len(SPEEDS_MS)

    def speed_ms(self) -> int:
        return SPEEDS_MS[self.speed_index]

    def advance_if_playing(self, model: ReplayViewModel) -> bool:
        """One playback tick; returns True if it actually advanced."""
        if not self.playing:
            return False
        if self.step >= self.max_step(model):
            self.playing = False
            return False
        self.step += 1
        return True

"""Batch 4A Task 4: status/event/connection-banner Tkinter panels.
Rendering-only, reads a :class:`LiveViewModel` snapshot."""

from __future__ import annotations

import tkinter as tk

from police_peer.gui.view_model import LiveViewModel

BANNER_TEXT = "LIVE VIEW — OPPONENT TRUE POSITION HIDDEN"
_RESULT_TEXT = {
    "capture": "SUB-GAME OVER: CAPTURE",
    "survival": "SUB-GAME OVER: SURVIVAL",
    "technical_loss": "SUB-GAME OVER: TECHNICAL LOSS",
    "disconnected": "OPPONENT DISCONNECTED",
    "timeout": "RESPONSE TIMEOUT",
}


class ConnectionBanner(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg="#7a1f1f")
        self.label = tk.Label(
            self, text=BANNER_TEXT, fg="white", bg="#7a1f1f", font=("Helvetica", 12, "bold")
        )
        self.label.pack(pady=4)
        self.result_label = tk.Label(
            self, text="", fg="yellow", bg="#7a1f1f", font=("Helvetica", 11)
        )
        self.result_label.pack()

    def render(self, model: LiveViewModel) -> None:
        text = _RESULT_TEXT.get(model.banner, "")
        self.result_label.config(text=text)


class StatusPanel(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.vars: dict[str, tk.StringVar] = {}
        for key in (
            "connection_status",
            "sub_game_number",
            "step",
            "state_machine_state",
            "strategy_class",
            "barriers_remaining",
            "config_sha256_prefix",
            "decision_latency_seconds",
            "belief_entropy_bits",
            "last_message_type",
            "commit_sent",
            "ack_received",
            "reveal_sent",
            "reveal_received",
        ):
            self.vars[key] = tk.StringVar(value="-")
            row = tk.Frame(self)
            row.pack(fill="x", anchor="w")
            tk.Label(row, text=f"{key}:", width=22, anchor="w").pack(side="left")
            tk.Label(row, textvariable=self.vars[key], anchor="w").pack(side="left")

    def render(self, model: LiveViewModel) -> None:
        self.vars["connection_status"].set(model.connection_status)
        self.vars["sub_game_number"].set(str(model.sub_game_number))
        self.vars["step"].set(str(model.step))
        self.vars["state_machine_state"].set(model.state_machine_state)
        self.vars["strategy_class"].set(model.strategy_class)
        self.vars["barriers_remaining"].set(str(model.barriers_remaining))
        self.vars["config_sha256_prefix"].set(model.config_sha256_prefix)
        latency = model.decision_latency_seconds
        self.vars["decision_latency_seconds"].set(f"{latency:.4f}" if latency is not None else "-")
        self.vars["belief_entropy_bits"].set(
            f"{model.belief.entropy_bits:.3f}" if model.belief else "-"
        )
        self.vars["last_message_type"].set(model.last_message_type)
        self.vars["commit_sent"].set(str(model.commit_sent))
        self.vars["ack_received"].set(str(model.ack_received))
        self.vars["reveal_sent"].set(str(model.reveal_sent))
        self.vars["reveal_received"].set(str(model.reveal_received))


class EventPanel(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.listbox = tk.Listbox(self, height=12, width=48)
        self.listbox.pack(fill="both", expand=True)
        self._shown = 0

    def render(self, model: LiveViewModel) -> None:
        new_lines = model.event_log[self._shown :]
        for line in new_lines:
            self.listbox.insert("end", line)
        self._shown = len(model.event_log)
        if new_lines:
            self.listbox.see("end")

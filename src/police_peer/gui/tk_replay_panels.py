"""Batch 4A Task 7/8: replay-viewer info panels. Rendering-only."""

from __future__ import annotations

import tkinter as tk

from police_peer.gui.replay_view_model import ReplaySubGame, ReplayViewModel


class VerdictBanner(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.label = tk.Label(self, text="", font=("Helvetica", 14, "bold"), fg="white")
        self.label.pack(fill="x", pady=4)
        self.findings = tk.Listbox(self, height=4)
        self.findings.pack(fill="x")

    def render(self, model: ReplayViewModel) -> None:
        ok = model.verification_ok
        self.label.config(
            text=f"THIS PEER'S OWN REPLAY VERDICT: {model.verdict}"
            f" (opponent's own verdict: {model.thief.verdict})",
            bg="#1f7a1f" if ok else "#7a1f1f",
        )
        self.findings.delete(0, "end")
        for f in model.police.findings:
            self.findings.insert("end", f)


class DeclarationPanel(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.vars: dict[str, tk.StringVar] = {}
        for key in ("group_id", "config_sha256_prefix", "police_verdict", "thief_verdict"):
            self.vars[key] = tk.StringVar(value="-")
            row = tk.Frame(self)
            row.pack(fill="x", anchor="w")
            tk.Label(row, text=f"{key}:", width=20, anchor="w").pack(side="left")
            tk.Label(row, textvariable=self.vars[key], anchor="w").pack(side="left")

    def render(self, model: ReplayViewModel) -> None:
        decl = model.declaration or {}
        self.vars["group_id"].set(str(decl.get("group_id", "-")))
        self.vars["config_sha256_prefix"].set(model.config_sha256_prefix)
        self.vars["police_verdict"].set(model.police.verdict)
        self.vars["thief_verdict"].set(model.thief.verdict)


class StepInfoPanel(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.vars: dict[str, tk.StringVar] = {}
        for key in (
            "sub_game",
            "step",
            "police_move",
            "thief_move",
            "police_hint",
            "thief_hint",
            "capture_claim",
            "claim_response",
            "commit_hash_prefix",
            "score",
            "result",
        ):
            self.vars[key] = tk.StringVar(value="-")
            row = tk.Frame(self)
            row.pack(fill="x", anchor="w")
            tk.Label(row, text=f"{key}:", width=20, anchor="w").pack(side="left")
            tk.Label(row, textvariable=self.vars[key], anchor="w", wraplength=260).pack(side="left")

    def render(self, sub_game: ReplaySubGame | None, step: int) -> None:
        if sub_game is None:
            return
        self.vars["sub_game"].set(str(sub_game.sub_game_number))
        self.vars["step"].set(str(step))
        p = next((s for s in sub_game.police_steps if s.step == step), None)
        t = next((s for s in sub_game.thief_steps if s.step == step), None)
        self.vars["police_move"].set(p.move if p else "-")
        self.vars["thief_move"].set(t.move if t else "-")
        self.vars["police_hint"].set(p.hint if p else "-")
        self.vars["thief_hint"].set(t.hint if t else "-")
        self.vars["capture_claim"].set(str(p.capture_claim) if p and p.capture_claim else "-")
        self.vars["claim_response"].set(str(t.claim_response) if t else "-")
        self.vars["commit_hash_prefix"].set(p.commit_hash_prefix if p else "-")
        self.vars["score"].set(f"police {sub_game.police_score} / thief {sub_game.thief_score}")
        self.vars["result"].set(f"{sub_game.result} (winner: {sub_game.winner})")

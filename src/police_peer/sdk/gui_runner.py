"""Batch 4A Task 3/4: wires the real headless series runner (unchanged) to
a live Tkinter view via the GUI event bus/sink. This module is the ONLY
SDK-layer file that imports ``gui/`` -- ``services/`` itself never imports
Tkinter, so headless runs (``--no-gui``, all existing tests) are completely
unaffected.
"""

from __future__ import annotations

from pathlib import Path

from police_peer.gui.background_runner import BackgroundRunner
from police_peer.gui.event_queue import GuiEventBus
from police_peer.gui.tk_app import LiveGuiApp
from police_peer.sdk.game_runner import (
    print_summary,
    run_series_headless,
    summary_exit_code,
)
from police_peer.services import gui_sink


def run_gui(config_dir: Path, opponent_url: str, smoke: bool, artifacts_dir: Path | None) -> int:
    bus = GuiEventBus()
    gui_sink.set_sink(bus.publish)
    runner = BackgroundRunner(
        lambda: run_series_headless(config_dir, opponent_url, smoke, artifacts_dir=artifacts_dir)
    )

    def on_close() -> None:
        gui_sink.clear_sink()
        runner.stop()

    app = LiveGuiApp(bus, "police", on_close, is_finished=runner.done)
    runner.start()
    try:
        app.run()
    finally:
        gui_sink.clear_sink()
        runner.stop()
    if runner.result is not None:
        print_summary(runner.result)
        return summary_exit_code(runner.result)
    if runner.error is not None:
        print(f"gui run failed: {runner.error}")
        return 1
    return 1

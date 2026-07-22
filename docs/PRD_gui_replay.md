# PRD gui replay

## Purpose

Define the live GUI and post-game replay viewer.

## Requirements

- Live GUI shows only this peer's own true state — own position, own visited cells, own barriers, belief heatmap, scent evidence, step/sub-game, hints, own commit status. Never the opponent's true current cell.
- Replay viewer loads standardized logs, recomputes every hash live, displays VERIFIED or TAMPERED, shows both tracks only after the game ends.
- Headless-compatible architecture so tests don't require a display.

## Acceptance criteria (measurable)

- [x] A GUI-model unit test (headless) proves the opponent's true position is never present in any rendered state object — `tests/unit/test_gui_no_opponent_leak.py` (reflection-based scanner over every dataclass in `services/gui_events.py` and `gui/view_model.py`).
- [x] Replay of an untampered log reports VERIFIED — `tests/unit/test_replay_view_model.py::test_valid_six_sub_game_like_set_verified`, real demonstration in `integration_lab/evidence/batch4a/gui_demo/`.
- [x] Replay of a deliberately tampered log reports TAMPERED — `tests/unit/test_replay_view_model.py::test_tampered_artifacts_are_refused` (report-refusal path) and the real copied-and-tampered demonstration in `integration_lab/evidence/batch4a/replay_demo/` (`tampered_demo_output.txt`).

## Implementation notes (Batch 4A)

- Live GUI: `gui/view_model.py` (pure, headless), `gui/tk_app.py`/`tk_board.py`/`tk_panels.py`
  (Tkinter rendering), `gui/event_queue.py`/`background_runner.py` (thread-safe
  event bridge), fed by `services/gui_events.py`/`gui_sink.py`/`turn_gui_publish.py`.
  `peer --gui`/`--no-gui` CLI command.
- Replay viewer: `gui/replay_view_model.py`/`replay_steps.py`/`replay_playback.py`
  (pure, headless), `gui/tk_replay_app.py`/`tk_replay_board.py`/`tk_replay_panels.py`
  (Tkinter rendering). `replay [--gui] --police-artifacts <dir> --thief-artifacts <dir>`
  CLI command. Reuses `services/replay_verifier.py` unmodified for this
  peer's own artifacts only (see `docs/LIMITATIONS.md` for the cross-schema
  finding on the opponent's side).

## Out of scope (for now)

Public deployment / screenshots (manual, see `screenshots/README.md`, not fabricated).

Status: implemented and tested (Batch 4A). See `integration_lab/audit/PROGRESS.md`.

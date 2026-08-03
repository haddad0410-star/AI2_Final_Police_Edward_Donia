# Architecture — Police Peer

Canonical protocol reference: `_post4b_supplementary_evidence/audit/protocol_contract.md`.
This file is the role-local summary; if the two ever disagree, the audit copy wins
until reconciled.

## Component responsibilities (`src/police_peer/`)

| Package | Responsibility | Status (`LOCAL_READY`) |
|---|---|---|
| `sdk/` | Single public entry point; no business logic itself, delegates to the layers below | Implemented: `negotiation_runner.py` (handshake orchestration) and `game_runner.py` (full game-loop orchestration) |
| `domain/` | Board, movement/barrier rules, scoring, scent/pheromone model, belief fusion, own-state tracking, state machine, deadline/watchdog — pure game logic, no I/O | Implemented: `roles`, `positions`, `actions`, `hints`, `captures`, `board`, `rules`, `scoring`, `scent`, `belief_model`, `belief_updates`, `observations`, `state`, `state_machine`, `deadline`, `watchdog` |
| `protocol/` | Wire message dataclasses (turn/control/audit), canonical JSON serialization | Implemented, full lifecycle wiring: `envelope`, `messages_handshake`, `messages_evidence`, `messages_turn`, `messages_capture`, `messages_control` |
| `strategy/` | `BaselinePoliceBrain`, `BeliefCutoffPoliceBrain`, shared `BrainBase`/`Decision` contract | Implemented, tested, and used in real gameplay — see `config/police/game.toml` (baseline) vs `config/police_advanced/game.toml` (advanced); design rationale in `_post4b_supplementary_evidence/audit/strategy_proposals.md` |
| `infrastructure/` | FastMCP server/client, Gmail sender, rate limiter/Gatekeeper, transport-level concerns | Implemented: `mcp_server.py`/`mcp_client.py` (full tool surface: health/negotiate/propose_config/receive_turn/receive_move/submit_audit/receive_control), Gmail sender (dry-run default, real send gated behind Manual Gate C, never invoked) |
| `services/` | Cross-cutting orchestration (e.g. the peer runtime/state machine, deadline tracker, watchdog) built on top of `domain` + `protocol` + `infrastructure` | Implemented: `subgame_runtime.py`, `series_runtime.py`, `series_artifacts.py`, `replay_verifier.py`, `result_agreement.py`, `bilateral_verify.py`, and others |
| `gui/` | Live view + replay viewer; never displays the opponent's true position | Implemented (Batch 4A): `view_model.py`/`event_queue.py`/`background_runner.py` (pure/headless), `tk_app.py`/`tk_board.py`/`tk_panels.py` (live Tkinter rendering), `replay_view_model.py`/`replay_steps.py`/`replay_playback.py` (pure/headless), `tk_replay_app.py`/`tk_replay_board.py`/`tk_replay_panels.py` (replay Tkinter rendering) |
| `shared/` | Config loading/validation, logging setup, version info — no game logic | Implemented: `errors`, `config_sections`, `config_validation`, `config_models`, `private_config`, `rate_limits_model`, `config_loader`, `canonical_json` |

## Independence guarantees

- No import of `thief_peer` or `integration_lab` from this package.
- No shared log/config file path with the opponent process.
- No in-memory singleton shared across processes (impossible anyway — separate OS
  processes — but also never designed as if it were possible).

These are enforced by an isolation-verification script (development-workspace-only
tooling, not included in this single-repo package), most recently re-run against both
real repositories with zero violations as part of the `LOCAL_READY` finalization pass —
see `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`.

## State machine

See `docs/PLAN.md`. The full turn-by-turn state machine (`domain/state_machine.py`),
sub-game runtime (`services/subgame_runtime.py`), series runtime
(`services/series_runtime.py`), artifact writer (`services/series_artifacts.py`), and
replay verifier (`services/replay_verifier.py`) are all implemented and independently
verified — raw verification logs were produced during development in the full project
workspace and are not included in this single-repo package; see
`_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md` for the
current, authoritative status summary.

## Server lifecycle

`infrastructure/server_lifecycle.py::ManagedServer` owns a directly-built
`uvicorn.Server` for this peer's FastMCP HTTP app, so production code can
request a genuinely graceful stop instead of task cancellation (which does
not reliably close the listening socket — see the CHANGELOG entry).
`sdk/negotiation_runner.py` and `sdk/game_runner.py` both use it.

# Architecture — Police Peer

Canonical protocol reference: `integration_lab/audit/protocol_contract.md`. This file
is the role-local summary; if the two ever disagree, the integration_lab audit copy
wins until reconciled.

## Component responsibilities (`src/police_peer/`)

| Package | Responsibility | Batch 1 status |
|---|---|---|
| `sdk/` | Single public entry point; no business logic itself, delegates to the layers below | `negotiation_runner.py` implemented (minimal vertical slice orchestration only) |
| `domain/` | Board, movement/barrier rules, scoring, scent/pheromone model, belief fusion, own-state tracking — pure game logic, no I/O | Implemented: `roles`, `positions`, `actions`, `hints`, `captures`, `board`, `rules`, `scoring`, `scent`, `belief_model`, `belief_updates`, `observations`, `state` |
| `protocol/` | Wire message dataclasses (turn/control/audit), canonical JSON serialization | Schemas implemented (`envelope`, `messages_handshake`, `messages_evidence`, `messages_turn`, `messages_capture`, `messages_control`); full lifecycle wiring is a later batch |
| `strategy/` | `BaselinePoliceBrain`, `BeliefCutoffPoliceBrain`, shared `BrainBase`/`Decision` contract | Not started — design only, see `integration_lab/audit/strategy_proposals.md` |
| `infrastructure/` | FastMCP server/client, Gmail sender, rate limiter/Gatekeeper, transport-level concerns | `mcp_server.py`/`mcp_client.py` implemented (health/negotiate/config-hash-compare only); Gmail sender not started |
| `services/` | Cross-cutting orchestration (e.g. the peer runtime/state machine, deadline tracker, watchdog) built on top of `domain` + `protocol` + `infrastructure` | Not started |
| `gui/` | Live view + replay viewer; never displays the opponent's true position | **Implemented (Batch 4A)**: `view_model.py`/`event_queue.py`/`background_runner.py` (pure/headless), `tk_app.py`/`tk_board.py`/`tk_panels.py` (live Tkinter rendering), `replay_view_model.py`/`replay_steps.py`/`replay_playback.py` (pure/headless), `tk_replay_app.py`/`tk_replay_board.py`/`tk_replay_panels.py` (replay Tkinter rendering) |
| `shared/` | Config loading/validation, logging setup, version info — no game logic | Implemented: `errors`, `config_sections`, `config_validation`, `config_models`, `private_config`, `rate_limits_model`, `config_loader`, `canonical_json` |

## Independence guarantees

- No import of `thief_peer` or `integration_lab` from this package.
- No shared log/config file path with the opponent process.
- No in-memory singleton shared across processes (impossible anyway — separate OS
  processes — but also never designed as if it were possible).

These are enforced by `integration_lab/verify_isolation.py`, run against both real
repositories with zero violations as of Batch 1 (`integration_lab/evidence/
verify_isolation_output.json`).

## State machine

See `docs/PLAN.md`. Batch 1 proved only the two-process FastMCP HTTP
handshake; the full turn-by-turn state machine (`domain/state_machine/`),
sub-game runtime (`services/subgame_runtime.py`), series runtime
(`services/series_runtime.py`), artifact writer (`services/
series_artifacts.py`), and replay verifier (`services/replay_verifier.py`)
were added in Batch 2 and independently verified in session recovery step B
(`integration_lab/evidence/session_recovery_step_b/police_phase_10_12/`).

## Server lifecycle (session recovery step B)

`infrastructure/server_lifecycle.py::ManagedServer` owns a directly-built
`uvicorn.Server` for this peer's FastMCP HTTP app, so production code can
request a genuinely graceful stop instead of task cancellation (which does
not reliably close the listening socket — see the CHANGELOG entry and
`integration_lab/evidence/session_recovery_step_b/server_lifecycle/`).
`sdk/negotiation_runner.py` and `sdk/game_runner.py` both use it.

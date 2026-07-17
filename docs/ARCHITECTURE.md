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
| `gui/` | Live view + replay viewer; never displays the opponent's true position | Not started |
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

See `docs/PLAN.md`. Not implemented yet — Batch 1 only proves a real two-process
FastMCP HTTP handshake (health/negotiate/config-hash-compare/ack/shutdown); the
full turn-by-turn state machine lives in `services/` in a later batch.

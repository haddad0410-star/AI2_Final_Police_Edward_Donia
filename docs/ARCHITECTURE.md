# Architecture — Police Peer

Canonical protocol reference: `integration_lab/audit/protocol_contract.md`. This file
is the role-local summary; if the two ever disagree, the integration_lab audit copy
wins until reconciled.

## Component responsibilities (`src/police_peer/`)

| Package | Responsibility |
|---|---|
| `sdk/` | Single public entry point; no business logic itself, delegates to the layers below |
| `domain/` | Board, movement/barrier rules, scoring, scent/pheromone model, belief fusion, own-state tracking — pure game logic, no I/O |
| `protocol/` | Wire message dataclasses (turn/control/audit), canonical JSON serialization |
| `strategy/` | `BaselinePoliceBrain`, `BeliefCutoffPoliceBrain`, shared `BrainBase`/`Decision` contract |
| `infrastructure/` | FastMCP server/client, Gmail sender, rate limiter/Gatekeeper, transport-level concerns |
| `services/` | Cross-cutting orchestration (e.g. the peer runtime/state machine, deadline tracker, watchdog) built on top of `domain` + `protocol` + `infrastructure` |
| `gui/` | Live view + replay viewer; never displays the opponent's true position |
| `shared/` | Config loading/validation, logging setup, version info — no game logic |

## Independence guarantees

- No import of `thief_peer` or `integration_lab` from this package.
- No shared log/config file path with the opponent process.
- No in-memory singleton shared across processes (impossible anyway — separate OS
  processes — but also never designed as if it were possible).

These are enforced by a forbidden-dependency test once code exists (`tests/unit/` or
`tests/integration/`), not yet written.

## State machine

See `docs/PLAN.md`. Implemented in `services/` once Phase 4 begins.

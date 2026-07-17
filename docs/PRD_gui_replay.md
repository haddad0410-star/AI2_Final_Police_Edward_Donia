# PRD gui replay

## Purpose

Define the live GUI and post-game replay viewer.

## Requirements

- Live GUI shows only this peer's own true state — own position, own visited cells, own barriers, belief heatmap, scent evidence, step/sub-game, hints, own commit status. Never the opponent's true current cell.
- Replay viewer loads standardized logs, recomputes every hash live, displays VERIFIED or TAMPERED, shows both tracks only after the game ends.
- Headless-compatible architecture so tests don't require a display.

## Acceptance criteria (measurable)

- [ ] A GUI-model unit test (headless) proves the opponent's true position is never present in any rendered state object.
- [ ] Replay of an untampered log reports VERIFIED.
- [ ] Replay of a deliberately tampered log reports TAMPERED.

## Out of scope (for now)

Public deployment / screenshots (manual, see `screenshots/README.md`, not fabricated).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

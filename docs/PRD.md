# PRD — Police Peer

## Purpose

Define what this repository must deliver for the final project: an independent
Police peer that plays Distributed Cops-and-Robbers over FastMCP against
another group's peer, per the binding rules in
`integration_lab/audit/binding_parameters.json`.

## Scope

In scope: FastMCP server+client, local game state/physics, scent/belief model,
`BaselinePoliceBrain` + `BeliefCutoffPoliceBrain` strategies, SHA-256 commit-reveal,
live GUI + replay viewer, Gmail reporting (`gmail.send` only), the four JSON artifacts.

Out of scope: anything about the Thief peer's internals (separate
repo), a central referee/orchestrator holding both true positions, LLM-selected moves.

## Sub-PRDs

See `PRD_fastmcp_peer.md`, `PRD_game_rules.md`, `PRD_scent_belief.md`,
`PRD_strategy.md`, `PRD_commit_reveal.md`, `PRD_gui_replay.md`,
`PRD_gmail_reporter.md` for per-area detail.

## Measurable acceptance criteria (project-level)

- [ ] Two real, separate FastMCP HTTP processes (this peer + the opponent's) complete
      at least one full sub-game locally (`LOCAL_READY`).
- [ ] `scripts/verify_shared_config.py`-style byte/hash comparison passes on the shared
      `game.json` between both peers.
- [ ] `uv run pytest --cov=src --cov-fail-under=85` passes with zero Ruff violations.
- [ ] Every submitted `.py` file is <=150 meaningful lines.
- [ ] Replay viewer reports `VERIFIED`, not `TAMPERED`, on an untampered log.
- [ ] A tampered log is correctly reported as `TAMPERED` (security test).
- [ ] `num_games=6` in the shared league config; `num_games=1` exists only in
      `integration_lab/config_fixtures/game_smoke_1.json`.

None of the above is satisfied yet — this PRD exists before implementation, per Phase 0
of the master plan. Status tracked in `integration_lab/audit/PROGRESS.md`.

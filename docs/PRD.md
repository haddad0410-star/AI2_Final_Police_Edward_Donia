# PRD — Police Peer

## Purpose

Define what this repository must deliver for the final project: an independent
Police peer that plays Distributed Cops-and-Robbers over FastMCP against
another group's peer, per the binding rules in
`_post4b_supplementary_evidence/audit/binding_parameters.json`.

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

- [x] Two real, separate FastMCP HTTP processes (this peer + the opponent's) complete
      at least one full sub-game locally (`LOCAL_READY`).
- [x] `scripts/verify_shared_config.py`-style byte/hash comparison passes on the shared
      `game.json` between both peers.
- [x] `uv run pytest --cov=src --cov-fail-under=85` passes with zero Ruff violations.
- [x] Every submitted `.py` file is <=150 meaningful lines.
- [x] Replay viewer reports `VERIFIED`, not `TAMPERED`, on an untampered log.
- [x] A tampered log is correctly reported as `TAMPERED` (security test).
- [x] `num_games=6` in the shared league config; a `num_games=1` smoke-test fixture
      exists only in the development workspace (not included in this package) and is
      never used as the league default.

All of the above is now satisfied at `LOCAL_READY` (real, tested, passing — not
inferred). Not satisfied, and not claimed: `NETWORK_READY`, `LEAGUE_READY`, or
`SUBMISSION_READY` — those require the remaining manual gates (public endpoint, real
league opponent, Gmail OAuth send, NotebookLM export, repository visibility decision,
GitHub push), all requiring Edward's own explicit action. Status tracked in
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed — Session recovery step A

- `tests/integration/test_game_runner_http.py` — both tests pointed
  `run_subgame_headless`/`run_series_headless` at the real, shared
  `config/police/game.toml`, whose hardcoded `my_port = 8901` both tests'
  own internal server tried to bind, causing `OSError: address already in
  use` (surfaced as `SystemExit: 3` from uvicorn's `Server.startup()`).
  Investigating why the first test's server didn't free the port for the
  second surfaced a deeper finding: cancelling the `asyncio.Task` wrapping
  `FastMCP.run_http_async(...)` (the shutdown pattern used everywhere in
  this codebase, including production `infrastructure/server_lifecycle.py`)
  never actually closes the underlying listening socket — `uvicorn.Server
  ._serve()` only reaches its socket-closing `shutdown()` when its polling
  `main_loop()` returns normally after observing `should_exit`; there is no
  `try/finally` around it, so a raw cancel skips it, permanently leaking the
  socket for the rest of the process (verified by direct experiment, not a
  timing race).
  New `tests/_port_utils.py` gives every test that starts a real server a
  dynamically allocated free port, a private per-test copy of the real
  config with only the port substituted, and a genuinely graceful
  start/stop built on a directly-owned `uvicorn.Server`
  (`should_exit = True`, not task cancellation) — verified to actually
  release the port afterward. No production code was changed; this is
  entirely a test-infrastructure fix. See `integration_lab/evidence/
  session_recovery_step_a/police_port_fix/root_cause_and_fix.md`.

### Added — Implementation Batch 1
- Configuration: `shared/{errors,config_sections,config_validation,config_models,
  private_config,rate_limits_model,config_loader,canonical_json}.py` — loads and
  strictly validates `game.json`/`game.toml`/`rate_limits.json`, rejects private
  overrides of shared fields, computes SHA-256 of the raw shared config.
- Domain models: `Role`, `Position`/`Direction`, `MoveAction`/`StayAction`/
  `BarrierAction`, `Hint`, `CaptureClaim`/`CaptureResponse`/`SubGameOutcome`,
  `LocalObservation`/`PublicTurnEnvelope`, `LocalPeerState` — structurally guaranteed
  to hold only this peer's own truth plus public info (tested by field introspection).
- Board physics: `domain/board.py`, `domain/rules.py` (movement, barrier legality,
  capture rules, visually verified against the book, not HW6), `domain/scoring.py`.
- Scent model: exact 5x5 emission matrix + decay formula (`domain/scent.py`).
- Belief model: normalized probabilistic belief update — prior, transition, scent
  likelihood, calibrated hint likelihood, entropy, top-k (`domain/belief_model.py`,
  `domain/belief_updates.py`); see `docs/BELIEF_MODEL.md`.
- Protocol schemas: strict validation for every message category (health,
  declaration, config proposal, ack, turn commit/reveal, public envelope, hint,
  scent payload, barrier declaration, capture claim/response, audit submission,
  control, error) — `protocol/*.py`.
- Minimal real FastMCP HTTP vertical slice: `infrastructure/mcp_server.py` (health,
  negotiate, propose_config tools), `infrastructure/mcp_client.py`,
  `sdk/negotiation_runner.py`, `__main__.py negotiate-smoke` — proven over a real
  two-independent-process HTTP handshake (not mocked).
- 100 tests, 94.43% coverage, 0 Ruff violations, all files <=150 meaningful lines.

### Not yet implemented
- Full turn-by-turn game loop, commit-reveal/audit lifecycle, strategy brains, state
  machine/DeadlineTracker/Watchdog, GUI, replay viewer, Gmail reporter, league runner.
  See `integration_lab/audit/PROGRESS.md` for the current readiness level (still
  below `LOCAL_READY`).

# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed — Implementation Batch 3.5 (observation-pipeline repair)

- `domain/crypto/payload.py::SealedTurnPayload` gained a real `scent_grid`
  field (schema `commit-reveal/2`); the raw scent grid now actually crosses
  the wire in the reveal body, not just a `scent_digest` hash of it — the
  root cause of Police's belief never receiving real scent evidence.
- `infrastructure/http_transport.py::_to_reveal` now reads
  `scent_grid`/`claim_response` directly from the reveal body, instead of
  scanning for standalone `"scent"`/`"capture_response"` message types
  that no sender ever produced (dead scaffolding, removed from
  `KNOWN_TURN_TYPES`) — a second, independent defect. The
  `claim_response` fix means **capture confirmation can now actually
  reach Police**, found while building Task 9's real-HTTP capture sanity
  fixtures.
- `intent` (the hint's truth/lie verdict) removed from
  `public_reveal_dict()` — now sealed until the final audit like `nonce`,
  per the "truth/lie intent sealed" rule (was previously disclosed at
  reveal time, defeating the purpose of tracking hint reliability from
  consistency).
- New `domain/scent_validation.py` (malformed/missing scent takes an
  explicit missing-evidence path) and `domain/hint_region.py`
  (region-word encode/decode for outgoing/incoming hints, including a
  genuine false-region choice when lying — previously Police's hint region
  was random regardless of intent, carrying no real signal even in
  principle).
- `services/belief_update.py::advance_belief` now folds in real scent
  (when valid) and hint evidence (when decoded), in the frozen order
  documented in `docs/BELIEF_MODEL.md`; added consistency-based hint-trust
  tracking (entropy-delta), never derived from the sealed `intent` field.
- `strategy/belief_cutoff_config.py`: `barrier_confidence_gate` split out
  as an independent field from `barrier_utility_floor` (previously one
  field served two purposes with opposite sensitivities — the confidence
  gate was mathematically unreachable given the real ~0.30 belief-
  confidence ceiling under continuous evidence). Defaults retuned to
  achievable values.
- `services/turn_loop.py::_result`: `steps` now derives from
  `len(records)` (the actual log length) instead of a separate turn
  counter, fixing a real replay-verifier `TAMPERED` finding surfaced by
  the first working capture scenario (the one-turn-delayed confirmation
  appends one more record than the counter had reached).
- 49 new tests (scent/hint transport, belief order, barrier lifecycle,
  strategy-pipeline integration) — 305 -> 354 tests, coverage 96.53% ->
  96.07%.
- Held-out (400 games) and real-HTTP (18 sub-games, 3 series) results:
  Police capture rate 0% -> 100% in every matchup (new ceiling tie,
  honestly analyzed, not claimed as strategy superiority). Full analysis:
  `integration_lab/evidence/batch3_5/`.

### Added — Implementation Batch 3

- `strategy/belief_cutoff_police_brain.py` (+ `belief_cutoff_config.py`,
  `belief_cutoff_utility.py`, `belief_cutoff_hint_trust.py`): original
  advanced Police strategy. Full-belief-distribution pursuit (not just
  argmax), bounded belief-transition lookahead, entropy-gated pursuit/
  exploration switching, real BFS-based barrier-placement evaluation
  (reachable-area reduction) gated by belief confidence, a hint-trust proxy
  (entropy-delta based — the wire protocol does not currently deliver raw
  hint text to strategy code; documented in `docs/STRATEGY.md`), and a
  documented, configurable utility function. 22 unit tests.
- `strategy/decision.py::DecisionRequest` gained `board`/`barriers_remaining`/
  `visited` fields (default-backed, `BaselinePoliceBrain` unaffected).
- `services/subgame_state.py::RuntimeState.with_barrier_placed` +
  `services/turn_loop.py` now actually apply a strategy's chosen barrier to
  local state and decrement the quota — previously dead code, since
  `BaselinePoliceBrain` never places one; exercised for the first time by
  `BeliefCutoffPoliceBrain`.
- `strategy/loader.py::load_police_brain` gained an optional `weights`
  parameter, passed through only when the resolved class's constructor
  accepts one.
- `shared/private_config.py::StrategyConfig` gained `profile`
  (`baseline`/`advanced`/`experiment`) and `weights` (validated numeric-
  only, unknown-key-rejecting) fields, selected via each peer's own private
  `game.toml` — never the signed shared `game.json`.
- Held-out research evaluation (100 games, seeds 2000-2099) and 3 real
  six-sub-game HTTP series found **no demonstrated capture-rate
  improvement** over `BaselinePoliceBrain` in the current experimental
  configuration — root cause and two bounded redesign iterations
  documented in `integration_lab/evidence/batch3/strategy_research/limitations.md`.
  Reported honestly as inconclusive, not hidden.
- `integration_lab/strategy_research/` (research-only local simulator,
  leakage tests, experiment runner, statistics, figures) and
  `integration_lab/run_advanced_strategy_series.py` (real HTTP validation
  launcher) — see `integration_lab/evidence/batch3/`.

### Changed — Session recovery step C

- Declaration schema frozen as canonical, versioned `declaration/2`
  (resolves `risk_register.md` risk #14). `domain/declaration.py` rewritten
  and split (150-line cap) into `declaration.py` (dataclass/to_dict/
  validate), `declaration_parsing.py` (`parse_declaration`, strict
  allow-list, alias normalization), `declaration_builder.py`
  (`DeclarationInputs`/`build_declaration`), `declaration_seal.py`
  (seal/verify/nonce/mismatches, moved unchanged). `hardware_probe.py`'s
  `HardwareInfo` gained `gpu_available`/`vram_gb`/`vram_status` (never
  fabricated — `None` + explanatory status when unavailable). New
  `content_sha256` commitment field. `services/series_artifacts.py` updated
  to the new `DeclarationInputs` call site. `declaration/1`-era aliases
  (`commit_hash`, `config_sha256`) accepted on input only, normalized,
  rejected if ambiguous. Canonical JSON Schema published at
  `docs/schemas/declaration.schema.json`, byte-identical (SHA-256
  `a995d657e81ed920f87f3ef39c3281550d346f38c18468cf7fdee79cd42a97bd`) to the
  independently-built Thief repo's copy; cross-repo fixture equivalence
  verified by `integration_lab/scripts/compare_declaration_schemas.py`.
  23 tests in `tests/unit/test_declaration.py` (was a smaller set pre-step-C).
  257 -> 270 tests, both Ruff/format clean. See
  `integration_lab/evidence/session_recovery_step_c/task2_declaration_schema/`
  and `.../declaration_schema_audit.md`.

### Fixed — Session recovery step B

- `infrastructure/server_lifecycle.py` — production HTTP shutdown still used
  raw `asyncio.Task.cancel()` after step A's test-only fix; direct
  experiment confirmed this never reaches `uvicorn.Server.shutdown()` (no
  `try/finally` around it in uvicorn's own `_serve()`), permanently leaking
  the listening socket. Rewritten around a new `ManagedServer` class: a
  directly-built `uvicorn.Server` gives production code a real handle to
  request a graceful stop (`should_exit`), escalate to a forced stop
  (`force_exit`) on a bounded timeout, and cancel only as a last resort —
  every outcome honestly classified via `ShutdownOutcome`/`ShutdownResult`.
  Refuses to bind to any host other than `127.0.0.1`/`localhost`/`::1`.
  `sdk/negotiation_runner.py` and `sdk/game_runner.py` updated to the new
  API; the old `ShutdownController`/`serve_until_shutdown`/`stop_server` API
  removed entirely. 11 new regression tests
  (`tests/integration/test_server_lifecycle.py`). See
  `integration_lab/evidence/session_recovery_step_b/server_lifecycle/`.
- `services/series_artifacts.py` (new) — artifact generation (Phase 11)
  existed and was unit-tested in isolation but was never called from
  `run_series_headless`/the CLI; a real `run-series` invocation produced no
  artifact files. Wired via a new `artifacts_dir` parameter and
  `run-series --artifacts-dir` CLI flag.
- `domain/declaration.py` — `PeerDeclaration` did not implement `validate()`,
  which the artifact-save layer requires; the first real attempt to save a
  declaration artifact raised `AttributeError`. Added `validate()` and a
  `to_dict()` alias.
- `services/replay_verifier.py` — could not detect a duplicate/relabeled
  sub-game record (a number-keyed dict lookup silently kept only the last
  one); added `_check_no_duplicate_sub_games` + a regression test.

See `integration_lab/evidence/session_recovery_step_b/police_phase_10_12/`
for the full verification writeup (series runtime and artifact
model/save layer were independently confirmed COMPLETE_AND_VERIFIED; the
above two items were the only genuine defects found).

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

# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed — Post-Batch-4B manual screenshot finalization

- **Peer-startup readiness race**: `peer --gui`/`run-series`/`run-subgame`
  sent the first real commit before the opponent's server/state machine
  was necessarily ready, causing a spurious `TECHNICAL_LOSS` on ordinary
  two-terminal human timing. Fixed with a bounded opponent-health wait
  (`services/subgame_runtime.py::await_opponent_ready`, reusing the
  existing `wait_for_health`) placed correctly — right after this peer's
  own machine leaves `INITIALIZING` (so it stays receptive to the
  opponent's first message the entire time it waits), never gated behind
  it. A genuine no-show still fails honestly at the first real exchange
  call, unchanged.
- **GUI protocol-status panel showed nothing real**: `commit_sent`/
  `ack_received`/`reveal_sent`/`reveal_received` existed in the view model
  but `gui/tk_panels.py`'s `StatusPanel` never rendered them, and
  `services/turn_gui_publish.py` had hardcoded `commit_sent=True` and
  collapsed the other three onto one pass/fail flag. Fixed:
  `infrastructure/http_transport.py::exchange_turn` now tracks the REAL
  per-substep progress of each commit/reveal exchange (extended
  `services/transport.py::TechnicalFailure` with `commit_sent`/
  `commit_acked`/`reveal_sent`), `turn_gui_publish.py` reads them instead
  of hardcoding, and `tk_panels.py` renders all four. New
  `tests/unit/test_turn_gui_publish.py` and additions to
  `tests/unit/test_http_transport.py` prove the values differ correctly
  across 4 distinct real failure modes.
- **`McpError` (client-side session-initialize timeout) crashed instead of
  retrying**: the readiness fix above calls `wait_for_health` far more
  often than before (previously only `negotiate-smoke`), which newly
  exposed a pre-existing gap in `infrastructure/mcp_client.py` — a
  connection/session-initialization timeout
  (`"Timed out while waiting for response to InitializeRequest"`) is
  raised by the installed `mcp`/`fastmcp` packages as `McpError`, which
  wasn't in `_CONNECTION_FAILURES` and so propagated uncaught instead of
  becoming `PeerUnavailableError`. Fixed narrowly: only an `McpError` whose
  `error.code == httpx.codes.REQUEST_TIMEOUT` (the exact, verified code
  used by the only two client-side-timeout raise sites in the installed
  packages) is reclassified as `PeerUnavailableError`; any other `McpError`
  (a genuine remote/application error) still propagates unchanged. New
  `tests/unit/test_mcp_client.py` (6 tests, fully monkeypatched/
  deterministic). The regression this fixes: a real integration test that
  used to take 30.17s (retry-then-crash) now takes 0.2-0.5s.
- New non-destructive `config/police_advanced` profile (identical to
  `config/police` except `[strategy].police_class` points at
  `BeliefCutoffPoliceBrain`) so the barrier-placement screenshot is
  actually reachable — the default profile's `BaselinePoliceBrain` never
  places a barrier by design. The default `config/police` profile itself
  was never modified.
- 18 real, human-captured screenshots (9 per repo) added under
  `screenshots/`; both `screenshots/README.md` files corrected where they
  previously pointed at commands that couldn't produce the described
  capture. Full index:
  `_post4b_supplementary_evidence/batch4b/MANUAL_HANDOFF.md`.
- 458 tests, 94.15% coverage, 0 Ruff violations, all files <=150 meaningful
  lines.

### Added — Implementation Batch 4B (bilateral commitment verification)

- **Unified `commitment/1` sealed-record schema** (`domain/crypto/payload.py`):
  resolves the Batch 4A cross-schema finding — `state` (nested dict)
  replaced by a flat `position` field, `config_sha256` promoted to a real
  top-level field. Schema-version-aware `to_canonical_dict()` keeps all
  Batch 1-4A evidence self-verifiable unmodified.
- **Real bilateral verification**: `services/bilateral_verify.py` (new,
  shared by the GUI replay viewer and the Gmail report gate) lets this
  repo's own crypto module independently verify a genuine Thief
  `commitment/1` record, no cross-repo import. New role-consistency
  (`_check_role_fields`) and unknown-field (`_check_unknown_fields`)
  checks in `services/replay_checks.py`.
- **Fixed a real gap found via the bilateral tamper matrix**:
  `domain/crypto/audit.py::_check_sequence_contiguous` now also rejects a
  reveal order that doesn't match step order (previously tolerated pure
  reordering — an asymmetry against Thief's own stricter check).
  `verdict-banner` now shows `VERIFIED — BOTH PEERS INDEPENDENTLY VERIFIED`
  when both sides are fully bilaterally verified.
- **Gmail report bilateral gate**: `report --opponent-artifacts-dir <dir>`
  refuses to build a report unless full bilateral verification passes.
- Evidence: `_post4b_supplementary_evidence/batch4b/` — schema audit, 10
  byte-identical cross-repo test vectors, a 21-category bilateral tamper
  matrix (all detected, both directions), a real six-sub-game two-process
  FastMCP series with `FULL_BILATERAL_VERIFICATION=true` both sides, and
  bilaterally-gated Gmail dry-run evidence.
- 445 tests, 0 Ruff violations, all files <=150 meaningful lines.

### Added — Implementation Batch 4A (live GUI, replay viewer, Gmail
### dry-run reporting, public-network preparation)

- **Live GUI** (`gui/`, `services/gui_events.py`, `services/gui_sink.py`,
  `services/turn_gui_publish.py`, `services/turn_decide.py`): the real
  turn loop now optionally publishes typed, own-truth-only events through
  an off-by-default sink into a thread-safe queue; a pure Tkinter-free
  view model (`gui/view_model.py`) folds them into display state (22
  headless tests, including a reflection-based opponent-position-leak
  scanner). `services/turn_loop.py` gained ~15 lines of publish calls;
  split `turn_decide.py`/`turn_gui_publish.py` out to stay under the
  150-line cap. New `peer --gui`/`--no-gui` CLI command
  (`sdk/gui_runner.py`, `gui/tk_app.py`/`tk_board.py`/`tk_panels.py`,
  `gui/background_runner.py`). Real two-process runs (smoke + full
  six-sub-game series, `--gui`) completed and replay-verified.
- **Graphical replay viewer** (`gui/replay_view_model.py`,
  `gui/replay_steps.py`, `gui/replay_playback.py`,
  `gui/tk_replay_app.py`/`tk_replay_board.py`/`tk_replay_panels.py`, new
  `replay` CLI command): reuses `services/replay_verifier.py` unmodified.
  **Real defect found and fixed while building this**: this repo's own
  verifier cannot correctly recompute the opponent's differently-shaped
  (`sealed-turn/2` vs `commit-reveal/2`) commitment hashes, and would
  otherwise report a false TAMPERED on genuinely valid opponent data — the
  opponent's side is now loaded for display only, honestly labeled
  `NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE`, never a fabricated verdict.
  15 headless tests.
- **Gmail dry-run reporter** (`domain/gmail_report_schema.py`,
  `infrastructure/gmail_credentials.py`, `infrastructure/gmail_gatekeeper.py`,
  `infrastructure/gmail_sender.py`, `sdk/report_runner.py`, new `report`
  CLI command): structured-JSON report built from real artifacts;
  `gmail.send`-only scope enforced in code; real token-bucket
  Gatekeeper (rate limit, concurrency, bounded retries/backoff, queue
  depth, idempotency); refuses to build a report from artifacts that fail
  the real replay verifier. `--send` exists but was never invoked this
  batch (43 tests across gatekeeper/credentials/sender/schema/refusal).
  New optional `gmail-send` dependency group (google-auth/-oauthlib/
  api-python-client), never installed by default `uv sync`.
- **Public-network preparation, never activated**
  (`infrastructure/public_auth.py`, `docs/PUBLIC_NETWORK_SETUP.md`,
  updated `docs/LEAGUE_RUNBOOK.md`): bearer-token resolution/constant-time
  verification, tested (7 tests). The existing localhost-only bind guard
  in `infrastructure/server_lifecycle.py` is unchanged.
- **Reliability regression** (before any GUI work began, per explicit
  gating instruction): three consecutive real six-sub-game HTTP series
  plus one bounded injected-delay scenario (new diagnostic-only
  `DelayedPoliceBrain` test fixture) all passed cleanly.
- Workspace scripts (`check_public_endpoint.py`, `check_peer_auth.py`,
  `check_port_release.py`, `package_match_evidence.py`) — all
  preparation/verification only, no network calls, no packaging of
  unverified evidence. These scripts live in the multi-repo development
  workspace and are not included in this single-repo package.

### Added — Implementation Batch 3.6 (epistemic fairness, scent timing,
### capture correctness, and strategy distinguishability audit)

No production defects were found this batch (verification/audit only,
triggered by Batch 3.5's own 100%-capture ceiling result needing an
independent fairness check before being trusted).

- `tests/unit/test_hint_visibility_batch3_6.py` (3 tests): end-to-end
  proof that the hint intent verdict is absent from the live `reveal`
  payload and present/verifiable only at final audit.
- Corrected a documentation-only inaccuracy in
  `_post4b_supplementary_evidence/audit/protocol_contract.md` §3.2: the `scent_grid`
  field name was a project paraphrase of the book's prose, not a literal
  book-mandated identifier (confirmed via full-text PDF search) — the
  implemented field/semantics are unchanged.
- Full audit evidence (no code impact): quantitative information-leakage
  analysis (200 random walks over production `domain.scent`/
  `domain.belief_updates`), a 9-condition causal ablation harness, a
  capture-correctness boundary re-audit (Thief-side test), 6 deterministic
  strategy behavioral-difference fixtures, non-ceiling secondary metrics,
  an 800-game multi-scale `RESEARCH_ONLY` robustness check, 3 new
  research/production-equivalence tests, and a 4-series real HTTP
  validation run. Full audit evidence was produced during development in
  the full project workspace and is not included in this single-repo
  package (the 7 associated figures are bundled at
  `_post4b_supplementary_evidence/batch3_6_figures/`).

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
  honestly analyzed, not claimed as strategy superiority). Full analysis
  was produced during development in the full project workspace and is
  not included in this single-repo package.

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
  documented during development in the full project workspace (not
  included in this single-repo package). Reported honestly as
  inconclusive, not hidden.
- A research-only local simulator (leakage tests, experiment runner,
  statistics, figures) and a real-HTTP validation launcher script were
  used to produce this batch's evidence; both scripts and the underlying
  evidence live in the multi-repo development workspace and are not
  included in this single-repo package.

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
  verified by `compare_declaration_schemas.py` (development-workspace
  script, not included in this single-repo package; most recently
  re-confirmed PASS in item 18 of
  `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`).
  23 tests in `tests/unit/test_declaration.py` (was a smaller set pre-step-C).
  257 -> 270 tests, both Ruff/format clean. Full write-up produced during
  development in the full project workspace; not included in this
  single-repo package.

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
  (`tests/integration/test_server_lifecycle.py`). Full write-up produced
  during development in the full project workspace; not included in this
  single-repo package.
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

The full verification writeup (produced during development in the full
project workspace; not included in this single-repo package) independently
confirmed the series runtime and artifact model/save layer as
COMPLETE_AND_VERIFIED; the above two items were the only genuine defects
found.

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
  entirely a test-infrastructure fix. Full root-cause write-up produced
  during development in the full project workspace; not included in this
  single-repo package.

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
  See `_post4b_supplementary_evidence/audit/PROGRESS.md` for the current readiness level (still
  below `LOCAL_READY`).

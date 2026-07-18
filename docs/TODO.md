# TODO — Police Peer

| Phase | Task | Owner | Status | Dependency | Definition of Done | Evidence |
|---|---|---|---|---|---|---|
| 0 | Extract binding parameters, protocol contract, reuse plan, manual gates, risk register, strategy proposals, visual verification | Claude | DONE | — | Files exist with substantive content | `integration_lab/audit/*` |
| 1 | Create this repo's directory skeleton, git init | Claude | DONE | Phase 0 | Repo exists, `git init` run, no remote | `git -C police_peer log`, `git -C police_peer status` |
| 2 | Documentation skeletons, ADRs, config drafts | Claude | DONE | Phase 1 | All listed files exist with real content, not empty stubs | this file tree |
| 3 | Shared constitution: `game.json`/`game.toml`/`rate_limits.json` loaders + validation, `verify_shared_config.py` passes | Claude | DONE (Batch 1) | Phase 2 | Hash match printed for both peers' `game.json`; loaders reject invalid/missing/override configs | `integration_lab/scripts/verify_shared_config.py` output, `tests/unit/test_shared_config.py`, `test_private_config.py`, `test_rate_limits_config.py` (26 tests) |
| 4 (partial) | Minimal FastMCP server+client vertical slice: health/negotiate/config-hash-compare/ack/shutdown | Claude | DONE (Batch 1, vertical slice only) | Phase 3 | Real two-process HTTP round-trip succeeds | `integration_lab/evidence/negotiation_smoke/`, `tests/integration/test_mcp_negotiation.py` (7 tests), `test_negotiation_runner.py` (2 tests) |
| 4 (remainder) | Full game-loop protocol (turn commit/reveal/audit lifecycle) | — | NOT STARTED | Batch 1 slice | Real HTTP round-trip carries actual turns | integration test log |
| 5 | Game state/physics (board, rules, barriers, scoring) | Claude | DONE (Batch 1) | Phase 3 | Unit tests green | `tests/unit/test_rules.py` (15 tests), `test_scoring.py` (4 tests) |
| 6 | Scent + belief model | Claude | DONE (Batch 1) | Phase 4-5 | Belief sums to 1, no true-position leak | `tests/unit/test_scent.py` (10), `test_belief.py` (13), `docs/BELIEF_MODEL.md`, `integration_lab/evidence/{scent,belief}_reference_run.json` |
| 7 | `BaselinePoliceBrain` + `BeliefCutoffPoliceBrain`, experiments | — | NOT STARTED (design only, see `integration_lab/audit/strategy_proposals.md`) | Phase 5-6 | Raw CSV/JSON results, no unsupported claims | `reports/strategy_results.*` |
| 8 | SHA-256 commit-reveal + mutual audit (full lifecycle) | — | NOT STARTED (schemas only this batch) | Phase 4 | Tamper tests all detected | `tests/security/` |
| 9 | State machine, DeadlineTracker, Watchdog | — | NOT STARTED | Phase 4 | Failure drills pass | `tests/integration/` |
| 9b | Protocol message schemas (health/declaration/config-proposal/ack/commit/reveal/hint/scent/barrier/capture/audit/control/error) -- validation only, no lifecycle wiring yet | Claude | DONE (Batch 1) | Phase 4 | Strict validation + negative tests for every category | `tests/protocol/test_protocol_schemas.py` (23 tests), `docs/adr/ADR-0012-receive-move-alias-assessment.md` |
| 10 | Live GUI + replay viewer | — | NOT STARTED | Phase 5-8 | Replay shows VERIFIED on untampered log | manual screenshot per `screenshots/README.md` |
| 11 | Four JSON artifacts + schema validation | — | NOT STARTED | Phase 4,8 | Schema tests pass, negative tests too | `tests/protocol/` |
| 12 | Gmail reporting (`gmail.send` only, dry-run default) | — | NOT STARTED | Manual Gate C | Dry-run JSON produced, no real send without `--send` + your approval | `reports/gmail_dry_run.json` |
| 13 | Quality gates: coverage >=85%, Ruff clean, file-length check | Claude | DONE for Batch 1 scope (94.43% coverage, 0 Ruff violations, all files <=150 lines) -- not yet DONE for later-batch modules that don't exist yet | Batch 1 modules | CI green | `reports/batch1_quality_output.txt` |
| 14 | Two-process local integration series | — | NOT STARTED | Phase 4-13 | Full 6-sub-game series locally | `integration_lab/` evidence |
| 15 | Public network + league (manual gates) | You | NOT STARTED | Manual Gates A, B | Real remote match | league evidence bundle |
| 16 | Academic report finalized | — | NOT STARTED | Phase 7,14 | README complete with real data | this README |
| 17 | Git tag + push (manual approval) | You | NOT STARTED | all above | `v1.0-submission` tag, pushed | `git log --tags` |
| 18 | Final audit + clean packaging | — | NOT STARTED | Phase 17 | ZIP validated | `reports/final_audit.*` |

Do not mark a task DONE before its evidence file exists — see `CLAUDE.md`'s
no-fabricated-evidence rule.

## Session recovery step C (this session)

Resolved the declaration schema divergence (risk #14, canonical
`declaration/2`); verified all four artifact contracts compatible; ran a
real FastMCP lifecycle regression (3x); ran a REAL one-sub-game two-process
HTTP game (Phase 4/14 in the table above, first real cross-process game);
ran a real six-sub-game two-process HTTP series (Phase 14); ran the mutual
cross-repo audit (96/96 checks passed); ran 18 bounded failure drills (Phase
9); ran full quality/security/reproducibility gates (Phase 13). Six real
cross-repo protocol defects found and fixed only by actually running two
independent processes — see `CHANGELOG.md` and
`integration_lab/audit/risk_register.md` risks #15-#16. Phases 4 (remainder),
9, 11, 13, 14 in the table above should now be read as DONE per this step's
evidence (`integration_lab/evidence/session_recovery_step_c/`); the table
itself predates Batch 2/step C numbering — treat `PROGRESS.md` as the
current source of truth. Readiness: `LOCAL_READY`.

## Session recovery step A (this session)

The Batch 2 background agent for this repo was killed mid-run by
infrastructure failures (not task-logic failures) with a large amount of
uncommitted Phase 3-12-range work in progress (see `integration_lab/
evidence/session_recovery/recovery_notes.md`). This recovery step fixed only
the one specific bug that agent was mid-fix on (a real HTTP test port
collision — see `integration_lab/evidence/session_recovery_step_a/
police_port_fix/`) plus quality gates; it did not implement any additional
phases, run a real two-process series, or advance readiness past
`LOCAL_READY`. The phase table above still reflects Batch 1 status only and
has not been re-audited phase-by-phase against the uncommitted Batch 2 work
in this recovery step — that re-audit is Recovery Step B+ work, not this
step.

## Session recovery step B (this session)

Fixed the production FastMCP/Uvicorn shutdown defect step A found but left
unfixed in production code (see `CHANGELOG.md`). Independently verified
Phases 10-12 against `protocol_contract.md`/`requirements_matrix.md`: the
series runtime and artifact model/save layer were already
COMPLETE_AND_VERIFIED; two genuine defects were found and fixed (artifact
generation not wired into `run-series`, and a duplicate-sub-game-number gap
in the replay verifier) — see `integration_lab/evidence/
session_recovery_step_b/police_phase_10_12/`. Still not implemented or
integration-tested: a real two-process series with an actual Thief
opponent, the mutual cross-repo audit, GUI, replay viewer (Phase 10 in this
table), Gmail (Phase 12 in this table), public network/league play (Phase
15), or advanced strategy (`BeliefCutoffPoliceBrain`, Phase 7). The phase
table's numbering above predates Batch 2 and does not line up 1:1 with the
Batch-2 phase numbers used in `integration_lab/audit/PROGRESS.md` and the
CHANGELOG — treat the table above as historical (Batch 1) and the CHANGELOG
+ PROGRESS.md as the current source of truth for Batch 2 status.

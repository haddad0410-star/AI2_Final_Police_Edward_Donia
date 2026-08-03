# TODO — Police Peer

| Phase | Task | Owner | Status | Dependency | Definition of Done | Evidence |
|---|---|---|---|---|---|---|
| 0 | Extract binding parameters, protocol contract, reuse plan, manual gates, risk register, strategy proposals, visual verification | Claude | DONE | — | Files exist with substantive content | `_post4b_supplementary_evidence/audit/*` |
| 1 | Create this repo's directory skeleton, git init | Claude | DONE | Phase 0 | Repo exists, `git init` run, no remote | `git -C police_peer log`, `git -C police_peer status` |
| 2 | Documentation skeletons, ADRs, config drafts | Claude | DONE | Phase 1 | All listed files exist with real content, not empty stubs | this file tree |
| 3 | Shared constitution: `game.json`/`game.toml`/`rate_limits.json` loaders + validation, `verify_shared_config.py` passes | Claude | DONE (Batch 1) | Phase 2 | Hash match printed for both peers' `game.json`; loaders reject invalid/missing/override configs | byte-for-byte hash match confirmed (produced during development, script itself not bundled in this package), `tests/unit/test_shared_config.py`, `test_private_config.py`, `test_rate_limits_config.py` |
| 4 (partial) | Minimal FastMCP server+client vertical slice: health/negotiate/config-hash-compare/ack/shutdown | Claude | DONE (Batch 1, vertical slice only) | Phase 3 | Real two-process HTTP round-trip succeeds | `tests/integration/test_mcp_negotiation.py`, `test_negotiation_runner.py` |
| 4 (remainder) | Full game-loop protocol (turn commit/reveal/audit lifecycle) | Claude | DONE | Batch 1 slice | Real HTTP round-trip carries actual turns, both peers verify a full sub-game and series | `tests/integration/`, real bilateral series evidence in `_post4b_supplementary_evidence/batch4b/bilateral_series/` |
| 5 | Game state/physics (board, rules, barriers, scoring) | Claude | DONE (Batch 1) | Phase 3 | Unit tests green | `tests/unit/test_rules.py`, `test_scoring.py` |
| 6 | Scent + belief model | Claude | DONE (Batch 1) | Phase 4-5 | Belief sums to 1, no true-position leak | `tests/unit/test_scent.py`, `test_belief.py`, `docs/BELIEF_MODEL.md` |
| 7 | `BaselinePoliceBrain` + `BeliefCutoffPoliceBrain`, experiments | Claude | DONE | Phase 5-6 | Raw CSV/JSON results, no unsupported claims | `src/police_peer/strategy/baseline_police_brain.py`, `belief_cutoff_police_brain.py`, `config/police/game.toml` vs `config/police_advanced/game.toml`, `docs/STRATEGY.md`, `_post4b_supplementary_evidence/audit/strategy_proposals.md` |
| 8 | SHA-256 commit-reveal + mutual audit (full lifecycle) | Claude | DONE | Phase 4 | Tamper tests all detected | `tests/security/`, `_post4b_supplementary_evidence/batch4b/tamper_matrix/` |
| 9 | State machine, DeadlineTracker, Watchdog | Claude | DONE | Phase 4 | Failure drills pass | `tests/integration/`, `src/police_peer/domain/state_machine.py`, `domain/deadline.py`, `domain/watchdog.py` |
| 9b | Protocol message schemas (health/declaration/config-proposal/ack/commit/reveal/hint/scent/barrier/capture/audit/control/error) -- validation only, no lifecycle wiring yet | Claude | DONE (Batch 1) | Phase 4 | Strict validation + negative tests for every category | `tests/protocol/test_protocol_schemas.py`, `docs/adr/ADR-0012-receive-move-alias-assessment.md` |
| 10 | Live GUI + replay viewer | Claude | DONE (Batch 4A) | Phase 5-8 | Replay shows VERIFIED on untampered log | manual screenshot per `screenshots/README.md`, `src/police_peer/gui/`, `_post4b_supplementary_evidence/batch4b/graphical_replay_regression/` |
| 11 | Four JSON artifacts + schema validation | Claude | DONE | Phase 4,8 | Schema tests pass, negative tests too | `tests/protocol/`, `src/police_peer/services/artifact_builders.py`, `artifact_models.py` |
| 12 | Gmail reporting (`gmail.send` only, dry-run default) | Claude | DONE (dry-run only; real send gated behind Manual Gate C, never invoked) | Manual Gate C | Dry-run JSON produced, no real send without `--send` + your approval | `_post4b_supplementary_evidence/batch4a_gmail_dry_run/` |
| 13 | Quality gates: coverage >=85%, Ruff clean, file-length check | Claude | DONE, real and current (real, tested, passing — `uv run pytest`/`ruff check`/`ruff format --check`/`scripts/check_file_lengths.py` all clean; coverage comfortably above the 85% floor) | all modules | CI green | `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md` |
| 14 | Two-process local integration series | Claude | DONE (real bilateral series run repeatedly over real localhost FastMCP, including a real bilateral result-agreement over HTTP) | Phase 4-13 | Full 6-sub-game series locally | `_post4b_supplementary_evidence/batch4b/bilateral_series/`, `_post4b_supplementary_evidence/batch4b/bilateral_static_proof/` |
| 15 | Public network + league (manual gates) | You | NOT STARTED (Manual Gates A, B genuinely open) | Manual Gates A, B | Real remote match | league evidence bundle |
| 16 | Academic report finalized | Claude | DONE — README.md contains real abstract, architecture, scent/belief formulas, strategy description, and results-across-batches sections drawn from actual development history | Phase 7,14 | README complete with real data | this repo's `README.md` |
| 17 | Git tag + push (manual approval) | You | NOT STARTED (Gate F, requires your explicit push approval) | all above | `v1.0-submission` tag, pushed | `git log --tags` |
| 18 | Final audit + clean packaging | Claude | DONE (LOCAL_READY packaging/audit pass completed; final GitHub push/tag still gated on Phase 17) | Phase 17 (for the push step only) | ZIP validated | `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md` |

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
`_post4b_supplementary_evidence/audit/risk_register.md` risks #15-#16. Phases
4 (remainder), 9, 11, 13, 14 in the table above were read as DONE per this
step's evidence (produced during development in the full project workspace,
not included in this single-repo package); the table itself predated Batch
2/step C numbering at the time — treat `PROGRESS.md` as the current source
of truth. Readiness: `LOCAL_READY`.

## Session recovery step A (this session)

The Batch 2 background agent for this repo was killed mid-run by
infrastructure failures (not task-logic failures) with a large amount of
uncommitted Phase 3-12-range work in progress (recovery notes were produced
during development in the full project workspace, not included in this
single-repo package). This recovery step fixed only the one specific bug
that agent was mid-fix on (a real HTTP test port collision; fix notes
likewise produced during development, not included in this package) plus
quality gates; it did not implement any additional phases, run a real
two-process series, or advance readiness past `LOCAL_READY`. At the time,
the phase table above still reflected Batch 1 status only and had not been
re-audited phase-by-phase against the uncommitted Batch 2 work in this
recovery step — that re-audit was Recovery Step B+ work, not this step.

## Session recovery step B (this session)

Fixed the production FastMCP/Uvicorn shutdown defect step A found but left
unfixed in production code (see `CHANGELOG.md`). Independently verified
Phases 10-12 against `protocol_contract.md`/`requirements_matrix.md`: the
series runtime and artifact model/save layer were already
COMPLETE_AND_VERIFIED; two genuine defects were found and fixed (artifact
generation not wired into `run-series`, and a duplicate-sub-game-number gap
in the replay verifier — evidence produced during development in the full
project workspace, not included in this single-repo package). At the time,
still not implemented or integration-tested: a real two-process series with
an actual Thief opponent, the mutual cross-repo audit, GUI, replay viewer
(Phase 10 in this table), Gmail (Phase 12 in this table), public
network/league play (Phase 15), or advanced strategy
(`BeliefCutoffPoliceBrain`, Phase 7) — all since completed in later batches,
see the table above and the phases below. The phase table's numbering above
predated Batch 2 at the time and did not line up 1:1 with the Batch-2 phase
numbers used in `_post4b_supplementary_evidence/audit/PROGRESS.md` and the
CHANGELOG.

## Implementation Batch 4A (historical)

GUI (Phase 10 in the table above), replay viewer, and Gmail reporting
(Phase 12) became **DONE** in this batch (dry-run only for Gmail — real
send gated behind Manual Gate C, never invoked). Public network/league play
(Phase 15) remained preparation-only (Manual Gates A/B). See `CHANGELOG.md`
and `_post4b_supplementary_evidence/audit/PROGRESS.md` for full detail.

## Current status note

The phase table at the top of this file has been updated to reflect current
(post-Batch-4B, `LOCAL_READY`) status directly — it is no longer Batch-1-only
as the historical session-recovery notes above (retained for record) describe
at the time each was written. Only Phases 15 and 17 (and the push-only part
of Phase 18) remain open, and only because they require Edward's own manual
action on Gates A/B/F.

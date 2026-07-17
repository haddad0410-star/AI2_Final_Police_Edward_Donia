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

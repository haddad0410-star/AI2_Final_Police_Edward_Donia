# TODO — Police Peer

| Phase | Task | Owner | Status | Dependency | Definition of Done | Evidence |
|---|---|---|---|---|---|---|
| 0 | Extract binding parameters, protocol contract, reuse plan, manual gates, risk register, strategy proposals, visual verification | Claude | DONE | — | Files exist with substantive content | `integration_lab/audit/*` |
| 1 | Create this repo's directory skeleton, git init | Claude | DONE | Phase 0 | Repo exists, `git init` run, no remote | `git -C police_peer log`, `git -C police_peer status` |
| 2 | Documentation skeletons, ADRs, config drafts | Claude | IN PROGRESS | Phase 1 | All listed files exist with real content, not empty stubs | this file tree |
| 3 | Shared constitution: finalize `game.json`/`game.toml`/`rate_limits.json`, `verify_shared_config.py` passes | Claude | NOT STARTED | Phase 2 | Hash match printed for both peers' `game.json` | `integration_lab/scripts/verify_shared_config.py` output |
| 4 | FastMCP server+client, protocol implementation | — | NOT STARTED | Phase 3 | Real HTTP round-trip between two local processes | integration test log |
| 5 | Game state/physics (board, rules, barriers, scoring) | — | NOT STARTED | Phase 3 | Unit tests green | `tests/unit/` |
| 6 | Scent + belief model | — | NOT STARTED | Phase 4-5 | Belief sums to 1, no true-position leak | `tests/unit/test_belief.py` |
| 7 | `BaselinePoliceBrain` + `BeliefCutoffPoliceBrain`, experiments | — | NOT STARTED | Phase 5-6 | Raw CSV/JSON results, no unsupported claims | `reports/strategy_results.*` |
| 8 | SHA-256 commit-reveal + mutual audit | — | NOT STARTED | Phase 4 | Tamper tests all detected | `tests/security/` |
| 9 | State machine, DeadlineTracker, Watchdog | — | NOT STARTED | Phase 4 | Failure drills pass | `tests/integration/` |
| 10 | Live GUI + replay viewer | — | NOT STARTED | Phase 5-8 | Replay shows VERIFIED on untampered log | manual screenshot per `screenshots/README.md` |
| 11 | Four JSON artifacts + schema validation | — | NOT STARTED | Phase 4,8 | Schema tests pass, negative tests too | `tests/protocol/` |
| 12 | Gmail reporting (`gmail.send` only, dry-run default) | — | NOT STARTED | Manual Gate C | Dry-run JSON produced, no real send without `--send` + your approval | `reports/gmail_dry_run.json` |
| 13 | Quality gates: coverage >=85%, Ruff clean, file-length check | — | NOT STARTED | all above | CI green | `reports/*_output.txt` |
| 14 | Two-process local integration series | — | NOT STARTED | Phase 4-13 | Full 6-sub-game series locally | `integration_lab/` evidence |
| 15 | Public network + league (manual gates) | You | NOT STARTED | Manual Gates A, B | Real remote match | league evidence bundle |
| 16 | Academic report finalized | — | NOT STARTED | Phase 7,14 | README complete with real data | this README |
| 17 | Git tag + push (manual approval) | You | NOT STARTED | all above | `v1.0-submission` tag, pushed | `git log --tags` |
| 18 | Final audit + clean packaging | — | NOT STARTED | Phase 17 | ZIP validated | `reports/final_audit.*` |

Do not mark a task DONE before its evidence file exists — see `CLAUDE.md`'s
no-fabricated-evidence rule.

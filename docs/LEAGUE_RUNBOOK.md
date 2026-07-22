# League Runbook — Police Peer

**Current readiness: `LOCAL_READY`.** `NETWORK_READY`/`LEAGUE_READY`/
`SUBMISSION_READY` are not claimed — see `integration_lab/audit/PROGRESS.md`.

## Binding league requirements (Appendix F Table 18, visually confirmed)

- **6 sub-games** per full series against one opponent (constant, binding
  `game.json`, unchanged this batch).
- **Minimum 2 distinct opponents** required for a passing grade (`min_games_to_pass=2`).
- Maximum 10 games per team (`max_games_per_team=10`).
- Diversity reward: +10 for a new opponent (`diversity_reward=10`).

## What is real and working today (local only)

- Full commit-reveal turn protocol, state machine, scent/belief pipeline,
  capture/survival/technical-loss resolution: implemented, tested (440
  tests, 96%+ coverage as of Batch 4A), verified over real two-process
  FastMCP HTTP repeatedly (Batches 1-4A).
- Both peers' headless replay verifier and graphical replay viewer
  (`peer replay --gui`/headless): real, tested, run against real match
  evidence — see `integration_lab/evidence/batch4a/`.
- Gmail dry-run reporting (`peer report`): real, tested, produces a real
  structured JSON report body from real artifacts; refuses to report on
  unverified/tampered evidence. `--send` exists in code but has never
  been invoked (Gate C).
- `integration_lab/scripts/package_match_evidence.py`: packages one
  completed local match's both-sides artifacts into a reviewable bundle,
  refusing to package anything that doesn't independently verify first.

## Manual gates (cannot be completed by Claude — see `integration_lab/audit/manual_gates.md`)

- **Gate A**: public MCP endpoint + tunnel authentication. Preparation
  only exists so far — see `docs/PUBLIC_NETWORK_SETUP.md`. No tunnel
  started, no public endpoint tested.
- **Gate B**: real opponent identity, URL, agreed config, schedule. Not
  contacted.
- **Gate C**: Gmail OAuth consent + explicit send approval. Not run.
- **Gate E/F**: repository visibility decision, GitHub creation/push. Not
  done.

## Pre-match checklist (for when Gates A/B/C are eventually approved)

- [ ] Shared `game.json` hash-matches the opponent's copy
      (`integration_lab/scripts/verify_shared_config.py`).
- [ ] `integration_lab/scripts/check_public_endpoint.py <url>` and
      `check_peer_auth.py` pass.
- [ ] Both peers' health checks pass over the real public endpoint (only
      after Gate A is approved and activated — not yet).
- [ ] Step-0 hardware declaration exchanged and signed.
- [ ] All 6 sub-games run to completion (capture, survival, or technical loss).
- [ ] Mutual audit reports no tampering
      (`integration_lab/scripts/package_match_evidence.py` refuses
      otherwise).
- [ ] `result_<game_id>.json` produced and agreed by both sides.
- [ ] `integration_lab/scripts/check_port_release.py` shows no orphans
      after the match.
- [ ] Gmail report sent (only after your explicit approval each time —
      `peer report --send`).

This checklist has not been run against a real distinct opponent yet —
only local self-play matches (`agreement_status: "unverified_self_play"`
in every result artifact produced so far).

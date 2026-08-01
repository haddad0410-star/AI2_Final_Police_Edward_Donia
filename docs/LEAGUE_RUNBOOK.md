# League Runbook — Police Peer

**Current readiness: `LOCAL_READY`.** `NETWORK_READY`/`LEAGUE_READY`/
`SUBMISSION_READY` are not claimed — see
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

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
  evidence (raw evidence produced during development in the full project
  workspace; the current bundled bilateral series is at
  `_post4b_supplementary_evidence/batch4b/bilateral_series/`).
- Gmail dry-run reporting (`peer report`): real, tested, produces a real
  structured JSON report body from real artifacts; refuses to report on
  unverified/tampered evidence. `--send` exists in code but has never
  been invoked (Gate C).
- `package_match_evidence.py`: packages one completed local match's
  both-sides artifacts into a reviewable bundle, refusing to package
  anything that doesn't independently verify first. This script was
  developed and tested in the full project workspace; it is not included
  in this single-repo package.

## Manual gates (cannot be completed by Claude — see `_post4b_supplementary_evidence/audit/manual_gates.md`)

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
      (`verify_shared_config.py`; this check was already validated against
      self-play configs during development — item 17 of
      `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`
      — but the script itself is not included in this single-repo package,
      so an equivalent hash comparison must be performed manually against
      the real opponent's config).
- [ ] `check_public_endpoint.py <url>` passes (this script is not included
      in this single-repo package and has not yet been run against any
      real public endpoint — Gate A is still open) and `check_peer_auth.py`
      passes (bearer-token logic already validated during development —
      item 16 of
      `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`
      — though the script itself is not included in this package).
- [ ] Both peers' health checks pass over the real public endpoint (only
      after Gate A is approved and activated — not yet).
- [ ] Step-0 hardware declaration exchanged and signed.
- [ ] All 6 sub-games run to completion (capture, survival, or technical loss).
- [ ] Mutual audit reports no tampering (`package_match_evidence.py`
      refuses otherwise; script developed and tested in the full project
      workspace, not included in this single-repo package — the underlying
      tamper-detection logic it relies on is recorded in
      `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`).
- [ ] `result_<game_id>.json` produced and agreed by both sides.
- [ ] `check_port_release.py` shows no orphans after the match (script
      developed in the full project workspace, not included in this
      single-repo package; has not yet been run against a real match).
- [ ] Gmail report sent (only after your explicit approval each time —
      `peer report --send`).

This checklist has not been run against a real distinct opponent yet —
only local self-play matches (`agreement_status: "unverified_self_play"`
in every result artifact produced so far).

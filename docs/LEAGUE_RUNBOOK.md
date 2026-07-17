# League Runbook — Police Peer

## Binding league requirements (Appendix F Table 18, visually confirmed)

- **6 sub-games** per full series against one opponent (constant).
- **Minimum 2 distinct opponents** required for a passing grade (`min_games_to_pass=2`).
- Maximum 10 games per team (`max_games_per_team=10`).
- Diversity reward: +10 for a new opponent (`diversity_reward=10`).

## Manual gates (cannot be completed by Claude — see `integration_lab/audit/manual_gates.md`)

- Gate A: public MCP endpoint + tunnel authentication.
- Gate B: real opponent identity, URL, agreed config, schedule.
- Gate C: Gmail OAuth consent + explicit send approval.

## Pre-match checklist (once implementation exists)

- [ ] Shared `game.json` hash-matches the opponent's copy
      (`integration_lab/scripts/verify_shared_config.py`).
- [ ] Both peers' health checks pass.
- [ ] Step-0 hardware declaration exchanged and signed.
- [ ] All 6 sub-games run to completion (capture, survival, or technical loss).
- [ ] Mutual audit reports no tampering.
- [ ] `result_<game_id>.json` produced and agreed by both sides.
- [ ] Gmail report sent (or drafted, per your approval) to
      `rmisegal+uoh26finalgame@gmail.com`.

Not run yet. Readiness level: below `LOCAL_READY` — see
`integration_lab/audit/PROGRESS.md`.

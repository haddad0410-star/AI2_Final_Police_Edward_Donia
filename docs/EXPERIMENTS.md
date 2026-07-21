# Experiments — Police Peer

Metric list and the tuning/held-out seed split were pre-registered in
`integration_lab/audit/strategy_proposals.md` Sections 0 and 5, written before
any strategy code existed, specifically to prevent post-hoc seed selection or
cherry-picked comparisons. This file is kept current every batch — never
allowed to claim a result higher than the evidence in
`integration_lab/audit/PROGRESS.md` and `integration_lab/evidence/` supports.

## Current results (Implementation Batch 3.6)

- Held-out evaluation (400 games, Batch 3.5) and real HTTP validation (18
  sub-games, Batch 3.5) both show **100% Police capture rate in every
  matchup**. Batch 3.6 extended this with an 800-game multi-scale
  robustness check (4 configs — binding 7x7, 7x7 alt-start, 9x9, 11x11 —
  x 4 matchups x 50 held-out seeds, `RESEARCH_ONLY_NOT_BINDING_LEAGUE_EVIDENCE`,
  never replacing the binding 7x7 league result): the ceiling **persists at
  every board scale tested**, with mean steps scaling proportionally
  (12 -> 16 -> 20 as the board grows 7 -> 9 -> 11).
- `BeliefCutoffPoliceBrain` shows **no demonstrated capture-rate
  improvement** over `BaselinePoliceBrain` on this metric (both ceiling-tied
  at 100%). It does show real, non-ceiling secondary differences: mean
  belief-entropy reduction 3.27 vs baseline's 2.48 bits, and mean 6
  barriers placed/game vs baseline's 0 (Batch 3.6 Task 8, 50 paired
  seeds/matchup).
- 6 deterministic behavioral fixtures (Batch 3.6 Task 7) prove
  `BeliefCutoffPoliceBrain` and `BaselinePoliceBrain` choose genuinely
  different actions from identical inputs, without ever reading the true
  opponent position.
- A causal ablation across 9 evidence-source conditions (Batch 3.6 Task 5,
  50 seeds/condition) shows the no-evidence condition alone reproduces
  Batch 3's original 0%-capture symptom, isolating evidence delivery — not
  brain logic — as the actual lever behind the Batch 3 -> 3.5 reversal.
- Final classification (Batch 3.6 Task 12): **C** (the 100% ceiling is a
  genuine game-design property of this board/geometry and greedy
  pursuit/evasion dynamics, not an implementation artifact) **with D**
  (real, non-ceiling behavioral differences exist) **as a direct
  corollary**. Not A, not B, not E.

Full data and figures:
- `integration_lab/evidence/batch3_5/strategy_research/` (400-game
  held-out results, real HTTP series, `acceptance_criteria_evaluation.md`)
- `integration_lab/evidence/batch3_6/` (`secondary_metrics.csv/json`,
  `robustness_results.csv/json`, `causal_results.csv/json`,
  `strategy_behavioral_differences.md`, `conclusion.md`,
  `figures/*.png` — 7 figures)

No performance claim is made anywhere in this repository without the raw
data in the paths above to back it.

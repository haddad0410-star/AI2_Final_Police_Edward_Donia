# PRD scent belief

## Purpose

Define the scent emission/decay model and the belief-fusion algorithm.

## Requirements

- 5x5 scent grid, center intensity 0.9, decay 0.10/turn via `τ(t+1) = (1-ρ)·τ(t) + Δτ` (Ch.4.3, visually confirmed, Fig.4 heatmap matches: 0.9/0.62/0.42/0.20/0.14/0.04 radial falloff).
- Belief grid fuses: prior, opponent scent evidence, legal-movement transitions, barriers, hints (down-weighted on conflict with physical evidence) — never the opponent's true position.
- `pheromone_min_center_intensity=0.5` is NOT treated as mandatory (unverified against Appendix F) — represented, if at all, as an optional negotiated extension.

## Acceptance criteria (measurable)

- [x] Belief grid always sums to 1 — `domain/belief_model.py::normalize`,
      `tests/unit/test_belief.py` (13 tests, incl. degenerate all-zero fallback).
- [x] Physically impossible cells always receive zero probability —
      `domain/belief_updates.py::apply_barrier_mask`; a hint can never revive a
      hard-zeroed cell (tested explicitly).
- [x] No test can recover the opponent's exact true position from the belief grid —
      structural guarantee, enforced by
      `test_no_function_accepts_an_opponent_true_position_parameter` (signature
      introspection over every function in `belief_updates`, not just a convention).
- [x] Decay matches the book's formula to floating-point tolerance —
      `domain/scent.py::apply_turn`, `tests/unit/test_scent.py` (10 tests: exact
      center value, exact 5x5 matrix, edge/corner clipping, one/repeated decay,
      re-emission, zero floor). Real computed values saved in
      `integration_lab/evidence/scent_reference_run.json` and
      `belief_reference_run.json` (not fabricated).

Full writeup: `docs/BELIEF_MODEL.md` (explicitly not claiming Bayesian optimality).

## Out of scope (for now)

Strategy use of the belief grid (see PRD_strategy.md — still design only).

Status: scent + belief model implemented and tested (Batch 1). See
`integration_lab/audit/PROGRESS.md`.

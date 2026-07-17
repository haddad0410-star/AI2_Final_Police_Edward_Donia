# PRD scent belief

## Purpose

Define the scent emission/decay model and the belief-fusion algorithm.

## Requirements

- 5x5 scent grid, center intensity 0.9, decay 0.10/turn via `τ(t+1) = (1-ρ)·τ(t) + Δτ` (Ch.4.3, visually confirmed, Fig.4 heatmap matches: 0.9/0.62/0.42/0.20/0.14/0.04 radial falloff).
- Belief grid fuses: prior, opponent scent evidence, legal-movement transitions, barriers, hints (down-weighted on conflict with physical evidence) — never the opponent's true position.
- `pheromone_min_center_intensity=0.5` is NOT treated as mandatory (unverified against Appendix F) — represented, if at all, as an optional negotiated extension.

## Acceptance criteria (measurable)

- [ ] Belief grid always sums to 1.
- [ ] Physically impossible cells always receive zero probability.
- [ ] No test can recover the opponent's exact true position from the belief grid.
- [ ] Decay matches the book's formula to floating-point tolerance.

## Out of scope (for now)

Strategy use of the belief grid (see PRD_strategy.md).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

# PRD game rules

## Purpose

Define local game physics: board, movement, barriers, scoring, series structure.

## Requirements

- 7x7 board minimum, 4-orthogonal+STAY movement only, no diagonals (Appendix F Table 13/15, visually confirmed).
- Barrier placement restricted to the police's own cell or an orthogonally-adjacent cell; permanent; truthful declaration mandatory; placing on the thief's current cell is a capture (Ch.3.4 "Barrier Law", visually confirmed — see `integration_lab/audit/visual_verification.md`).
- max_barriers=14, max_moves=35, survival_threshold=35 (all minimums).
- Scoring: capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2 (all constants); technical_loss=0 (cross-confirmed, not a numbered Appendix F row).
- num_games=6 per series (constant, visually confirmed).

## Acceptance criteria (measurable)

- [x] All legal-move generation matches the negotiated `move_set` — `domain/rules.py::legal_move_directions`, `tests/unit/test_rules.py` (15 tests, incl. diagonal rejection, boundary rejection, barrier collision).
- [x] Barrier placement legality tests pass (adjacency + permanence + no self-removal) — `domain/rules.py::is_legal_barrier_cell`/`place_barrier`, same test file; see also `docs/adr/ADR-0011-trapped-thief-interpretation.md` for the STAY-always-legal interpretation.
- [x] Scoring unit tests match the table above exactly — `domain/scoring.py`, `tests/unit/test_scoring.py` (4 tests).
- [ ] A 6-sub-game series runs to completion locally — not yet; Batch 1 only proves a single negotiation handshake (`integration_lab/evidence/negotiation_smoke/`), not a played sub-game.

## Out of scope (for now)

Scent/belief model (see PRD_scent_belief.md — now implemented). Cryptographic sealing
(see PRD_commit_reveal.md — still not implemented, schemas only).

Status: board/rules/scoring implemented and tested (Batch 1); the full game loop that
would actually play a sub-game to completion is a later batch. See
`integration_lab/audit/PROGRESS.md`.

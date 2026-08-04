# PRD game rules

## Purpose

Define local game physics: board, movement, barriers, scoring, series structure.

## Requirements

- 7x7 board minimum, 4-orthogonal+STAY movement only, no diagonals (Appendix F Table 13/15, visually confirmed).
- Barrier placement restricted to the police's own cell or an orthogonally-adjacent cell; permanent; truthful declaration mandatory; placing on the thief's current cell is a capture (Ch.3.4 "Barrier Law", visually confirmed — see `_post4b_supplementary_evidence/audit/visual_verification.md`).
- max_barriers=14, max_moves=35, survival_threshold=35 (all minimums).
- Scoring: capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2 (all constants); technical_loss=0 (cross-confirmed, not a numbered Appendix F row).
- num_games=6 per series (constant, visually confirmed).

## Acceptance criteria (measurable)

- [x] All legal-move generation matches the negotiated `move_set` — `domain/rules.py::legal_move_directions`, `tests/unit/test_rules.py` (15 tests, incl. diagonal rejection, boundary rejection, barrier collision).
- [x] Barrier placement legality tests pass (adjacency + permanence + no self-removal) — `domain/rules.py::is_legal_barrier_cell`/`place_barrier`, same test file; see also `docs/adr/ADR-0011-trapped-thief-interpretation.md` for the STAY-always-legal interpretation.
- [x] Scoring unit tests match the table above exactly — `domain/scoring.py`, `tests/unit/test_scoring.py` (4 tests).
- [x] A 6-sub-game series runs to completion locally — real six-sub-game two-process
  FastMCP series completed with both sides' replay verifiers reporting
  `FULL_BILATERAL_VERIFICATION=true` (see `docs/SECURITY.md` Batch 4B section,
  README.md "Results across batches"). Batch 1's negotiation handshake proof was
  an early single-message smoke test only (development-workspace artifact, not
  included in this single-repo package); the full played series is what actually
  ships now.

## Out of scope (for now)

None — scent/belief model (see PRD_scent_belief.md) and cryptographic sealing
(see PRD_commit_reveal.md) are both implemented.

Status: board/rules/scoring, the full game loop, and a complete played
six-sub-game series are all implemented and tested. See
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

# PRD strategy

## Purpose

Define the strategy seam and the two brains for this role.

## Requirements

- `BrainBase` contract: `_pick_move(moves, state, belief) -> Decision`, legal-move-only output, deadline-aware, deterministic test mode.
- `BaselinePoliceBrain`: simple, original, from-scratch greedy baseline.
- `BeliefCutoffPoliceBrain`: implemented original design — full-belief-distribution pursuit, bounded lookahead, entropy-gated exploration, real barrier engineering via BFS reachable-area reduction; see `_post4b_supplementary_evidence/audit/strategy_proposals.md` Section 3/4 for the original design sketch this was built from.
- Move is always pure Python; LLM banter is optional, template provider by default (0 tokens).

## Acceptance criteria (measurable)

- [x] Both brains never return an illegal move across a large randomized test sweep — `tests/unit/test_baseline_brain.py::test_always_returns_a_legal_move_across_random_boards`, `tests/unit/test_belief_cutoff_brain.py::test_always_returns_legal_move_across_random_scenarios`.
- [x] Both brains always return within the deadline (fallback tested) — `tests/unit/test_baseline_brain.py::test_deadline_compliance_is_fast`, `tests/unit/test_belief_cutoff_brain.py::test_deadline_fallback_never_exceeds_budget`, `tests/unit/test_strategy_fallback.py`.
- [x] Phase 7 experiments compare candidate vs. baseline on held-out seeds only, with raw data saved — no win-rate superiority claim is made (see README.md "Results across batches"); raw data produced during development in the full project workspace, not included in this single-repo package.

## Out of scope (for now)

LLM-driven move selection (never in scope unless a signed mutual rule with the opponent explicitly enables it).

Status: implemented and tested; both brains are used in real gameplay. See
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

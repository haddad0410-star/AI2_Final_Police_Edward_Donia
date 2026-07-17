# PRD strategy

## Purpose

Define the strategy seam and the two brains for this role.

## Requirements

- `BrainBase` contract: `_pick_move(moves, state, belief) -> Decision`, legal-move-only output, deadline-aware, deterministic test mode.
- `BaselinePoliceBrain`: simple, original, from-scratch greedy baseline.
- `BeliefCutoffPoliceBrain`: candidate original design — see `integration_lab/audit/strategy_proposals.md` Section 3/4 for the full sketch.
- Move is always pure Python; LLM banter is optional, template provider by default (0 tokens).

## Acceptance criteria (measurable)

- [ ] Both brains never return an illegal move across a large randomized test sweep.
- [ ] Both brains always return within the deadline (fallback tested).
- [ ] Phase 7 experiments compare candidate vs. baseline on held-out seeds only, with raw data saved — no claim without it.

## Out of scope (for now)

LLM-driven move selection (never in scope unless a signed mutual rule with the opponent explicitly enables it).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

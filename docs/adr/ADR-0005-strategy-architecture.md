# ADR-0005: Strategy Architecture

## Status

Accepted

## Context

The book requires the move to always be chosen by pure Python (Appendix E rule 25), with the LLM strictly optional and banter-only.

## Decision

A `BrainBase` contract with `_pick_move`/`_decide_move`, injected via `game.toml`'s `[strategy]` section. Two implementations per role: `BaselinePoliceBrain` (simple, original baseline) and `BeliefCutoffPoliceBrain` (advanced, see `_post4b_supplementary_evidence/audit/strategy_proposals.md`). Both are now implemented, tested, and used in real gameplay (`config/police/game.toml` vs `config/police_advanced/game.toml`).

## Consequences

The strategy module is fully swappable without touching the engine, protocol, or JSON artifacts — matches the book's own "strategy seam" design (Ch.6.2).

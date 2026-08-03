# ADR-0009: Shared Game Json Vs Private Game Toml

## Status

Accepted

## Context

The book (Appendix B) requires a byte-identical, signed shared config (`game.json`) separate from private per-peer config (`game.toml`), so both sides provably agree on the same physics without leaking private setup details to the opponent.

## Decision

`config/police/game.json` holds only mutually-agreed, hashable terms (board, movement, scoring, pheromones, network/league, rate limits) drawn from `_post4b_supplementary_evidence/audit/binding_parameters.json`. `config/police/game.toml` holds only this peer's private setup (group identity, local port, opponent URL, strategy class choice, banter provider, Gmail settings) and must never weaken or override a signed `game.json` term.

## Consequences

A `verify_shared_config.py`-style byte/hash comparison (development-workspace-only tooling, not included in this single-repo package) must be run before every match to catch any accidental drift between the two peers' `game.json` copies.

# ADR-0009: Shared Game Json Vs Private Game Toml

## Status

Accepted

## Context

The book (Appendix B) requires a byte-identical, signed shared config (`game.json`) separate from private per-peer config (`game.toml`), so both sides provably agree on the same physics without leaking private setup details to the opponent.

## Decision

`config/police/game.json` holds only mutually-agreed, hashable terms (board, movement, scoring, pheromones, network/league, rate limits) drawn from `integration_lab/audit/binding_parameters.json`. `config/police/game.toml` holds only this peer's private setup (group identity, local port, opponent URL, strategy class choice, banter provider, Gmail settings) and must never weaken or override a signed `game.json` term.

## Consequences

`integration_lab/scripts/verify_shared_config.py` must be run before every match to catch any accidental drift between the two peers' `game.json` copies.

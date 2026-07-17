# ADR-0004: Sha256 Commit Reveal

## Status

Accepted

## Context

The book (Ch.5) requires a judge-free, cryptographically enforced commit-reveal protocol so neither side can rewrite history after seeing the opponent's move.

## Decision

Implement `H_commit = SHA256(canonical_json({state, move, intent, nonce}))`, fresh CSPRNG nonce per step, `secrets.compare_digest` for constant-time verification, full reveal only at the final mutual audit.

## Consequences

Every step incurs a hash computation and a nonce-storage obligation; audit logs must retain every payload+nonce pair until the series ends.

# ADR-0003: Canonical Json

## Status

Accepted

## Context

Commit-reveal hashing and `game_id`/`game_uid` derivation both require both peers to hash byte-identical input, or their independently-computed hashes will never match.

## Decision

All cryptographically-hashed payloads use canonical JSON: sorted keys, UTF-8, fixed separators `(",", ":")`, exactly as shown in the book's own `commit()`/`verify()` sample (Ch.5.3.2, printed p.37).

## Consequences

Any future field addition to a sealed payload must preserve this serialization discipline, or cross-peer hash verification silently breaks.

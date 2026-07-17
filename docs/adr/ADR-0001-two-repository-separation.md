# ADR-0001: Two Repository Separation

## Status

Accepted

## Context

The book (Appendix E rules 1-3) and this project's own rules require two fully independent processes, repos, and configs, with no central referee and no shared mutable state.

## Decision

`police_peer` and `thief_peer` are separate Git repositories, separate `pyproject.toml`s, separate Python packages (`police_peer`/`thief_peer`), never importing each other or `integration_lab` at runtime.

## Consequences

A forbidden-dependency test (Phase 5) must fail the build if either side imports the other, or if `integration_lab` is imported by either.

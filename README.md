# AI2 Final Project — Police Peer (police_peer)

**Status: Phase 1-2 scaffold. No application code implemented yet.**

## Abstract

_TODO (Phase 16): one-paragraph summary of the approach and headline results, written
only after real experiments exist. Not written yet — no results exist to summarize._

## Team

- Edward Haddad — 214083115
- Donia Naser — 212810493
- Provisional group ID: `edward-donia` (**configurable, requires final verification**
  against the course's binding group-ID assignment rule)

## Sibling repository

This is the **Police** peer. The **Thief** peer lives in a
separate, independent repository: `https://github.com/haddad0410-star/AI2_Final_Thief_Edward_Donia` (placeholder URL — not
yet created/pushed).

Per the project's isolation rules, this repository does **not** import from the sibling
repository or from `integration_lab/` at runtime. Any resemblance in wire format is by
shared protocol contract only (see `docs/PROTOCOL.md`).

## What this repo is (and isn't) right now

This scaffold contains: directory structure, documentation skeletons, ADRs, and draft
configuration files. It does **not** yet contain: a FastMCP server/client, a game engine,
a state machine, strategy logic, the scent/belief model, cryptographic commit-reveal, a
GUI, a replay viewer, or a Gmail reporter. Those are implemented in later phases, after
this scaffold is reviewed and approved.

## Problem formulation

Distributed Cops-and-Robbers is framed as a two-agent, partially-observable pursuit
game (Dec-POMDP-flavored): each peer observes only its own true state, the opponent's
public scent trail, and the opponent's (possibly deceptive) natural-language hints —
never the opponent's true position. See `docs/PLAN.md` for the formal diagrams and
`integration_lab/audit/protocol_contract.md` for the wire-level contract both peers
must satisfy to interoperate with any other group's implementation.

## Architecture (summary)

Two fully independent FastMCP peers (server + client in one process), no central
referee, no shared mutable state. Full detail in `docs/ARCHITECTURE.md`.

## Game rules (summary)

Binding numeric parameters come from Appendix F of the course's rule book, extracted
and visually verified in `integration_lab/audit/binding_parameters.json` and
`integration_lab/audit/visual_verification.md`. Headline values: 7x7 board (minimum),
4-orthogonal + STAY movement, up to 14 barriers, up to 35 moves, 35-step survival
threshold, 5x5 scent grid decaying at 0.10/turn from a center intensity of 0.9, and a
**6-sub-game** series per opponent (constant).

## Strategy (summary)

Two brains are planned for this role: `BaselinePoliceBrain` (a simple, original,
from-scratch greedy baseline — not a copy of the reference implementation) and
`BeliefCutoffPoliceBrain` (our candidate original strategy). Neither has been
implemented or benchmarked yet, and no superiority claim is made for either — see
`integration_lab/audit/strategy_proposals.md` for the full design and
`docs/STRATEGY.md` for the role-local summary.

## Commit-reveal / security (summary)

Every step is sealed with SHA-256 over canonical JSON before being revealed, and a
mutual end-of-game audit re-verifies every hash. See `docs/SECURITY.md`.

## GUI / replay (summary)

Planned: a live GUI showing only this peer's own true state (never the opponent's true
position), and a replay viewer that recomputes every hash and reports VERIFIED/TAMPERED.
Not implemented yet. See `docs/PRD_gui_replay.md`.

## Experiments

Not run yet. Tuning-seed vs. held-out-seed split is pre-registered in
`integration_lab/audit/strategy_proposals.md` Section 0, before any strategy code
exists, specifically to prevent post-hoc seed selection.

## Limitations

See `docs/LIMITATIONS.md` — kept current, updated every phase.

## Reproduction

```
uv sync
uv run python -m police_peer peer --role police --no-gui   # NOT YET IMPLEMENTED
```

## Third-party attribution

See `THIRD_PARTY_NOTICES.md`. Reused elements are limited to small, attributed
adaptations (a commit-reveal hash shape, a token-bucket formula, an OAuth bootstrap
pattern, a protocol naming convention) — never substantial verbatim code. Full
classification: `integration_lab/audit/reference_reuse_plan.md`.

## Submission tag

Not yet tagged. Will be `v1.0-submission` once `SUBMISSION_READY` (see
`integration_lab/audit/PROGRESS.md` for current readiness level, which remains below
`LOCAL_READY` as of this scaffold).

# AI2 Final Project — Police Peer (police_peer)

**Status: Implementation Batch 3.5.** Batch 3 found that held-out/real-HTTP
evaluation showed no demonstrated capture-rate improvement for
`BeliefCutoffPoliceBrain`, root-caused to a real observation-pipeline
defect: the wire protocol never actually delivered scent/hint evidence to
belief updates, and (found while repairing it) capture confirmation could
never reach Police at all. Batch 3.5 repairs both defects end to end (see
`integration_lab/evidence/batch3_5/pipeline_root_cause.md`) and
re-validates: held-out evaluation (400 games) and real HTTP validation (18
sub-games, 3 series) now show **100% Police capture rate in every
matchup** — a complete reversal from Batch 3's 0%, and real, functioning
barrier usage (previously never observed). This is a new ceiling tie
(capture, not survival); `BeliefCutoffPoliceBrain` shows no demonstrated
capture-RATE improvement over baseline (both 100%), but does show a real,
distinct barrier-driven capture mechanism (70% of captures against a
baseline Thief) — reported honestly, see
`integration_lab/evidence/batch3_5/strategy_research/acceptance_criteria_evaluation.md`.
GUI, Gmail reporting, public network exposure, and league play are **not**
implemented/run yet. Readiness: see
`integration_lab/audit/PROGRESS.md` for the current level.

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

## What's actually implemented (Batch 1)

- **Configuration**: strict loaders/validators for `game.json` (shared, byte-identical
  with `thief_peer`, SHA-256-verified), `game.toml` (private, rejects any attempt to
  override a shared field), `rate_limits.json`.
- **Domain models**: `Role`, `Position`/`Direction`, move/barrier/stay actions, hints,
  capture claim/response, `LocalPeerState` — structurally guaranteed (tested by field
  introspection, not just convention) to hold only this peer's own truth.
- **Board physics**: legal movement (4-orthogonal + STAY, no diagonals), barrier
  placement legality (own-cell or orthogonally-adjacent only, visually verified
  against the book), capture/scoring rules.
- **Scent + belief models**: exact 5x5 emission matrix and decay formula; a normalized
  probabilistic belief update (not claimed Bayesian-optimal) — see
  `docs/BELIEF_MODEL.md`.
- **Protocol schemas**: strict validation for every message category in
  `integration_lab/audit/protocol_contract.md`.
- **Minimal real FastMCP HTTP vertical slice**: `health`/`negotiate`/`propose_config`
  tools, proven over an actual two-independent-process HTTP handshake — evidence in
  `integration_lab/evidence/negotiation_smoke/`.
- **Batch 2 (verified in session recovery steps A/B)**: commit-reveal
  crypto, Step-0 declaration, state machine, deadline tracker + watchdog,
  extended FastMCP turn protocol, baseline strategy brain, template hints,
  sub-game runtime (Phase 9), six-sub-game series runtime (Phase 10), JSON
  artifact generation now wired into `run-series --artifacts-dir` (Phase
  11), and the headless replay verifier (`verify-replay`, Phase 12). A
  genuine production shutdown defect (task-cancellation not closing the
  Uvicorn listening socket) was found and fixed — see `CHANGELOG.md`.
- 305 tests, 96.53% coverage, 0 Ruff violations, every file ≤150 meaningful
  lines (Implementation Batch 3; see `integration_lab/evidence/batch3/quality/`).
- **354 tests, 96.07% coverage, 0 Ruff violations, every file ≤150 meaningful
  lines (Implementation Batch 3.5 — observation-pipeline repair; see
  `integration_lab/evidence/batch3_5/quality/`).**

## Session recovery step C (new)

Canonical `declaration/2` schema frozen and verified byte-identical to the
Thief repo's (risk #14, resolved). Real cross-process HTTP validated for the
first time: a 3x FastMCP lifecycle regression, a real one-sub-game series
(`survival`, winner thief, 35 steps, both replay verifiers `VERIFIED`), a
real six-sub-game series (6/6 games, mutual comparison 96/96 checks passed),
an independent tamper-detection check, and all 18 bounded failure drills —
all genuinely passing. Fixed 6 real defects found only by actually running
two independent processes against each other for the first time (sequence
numbering, reveal wire shape/delivery model, envelope field mismatch,
per-sub-game sequence scoping, inbox message accumulation) — see
`CHANGELOG.md` and `integration_lab/audit/risk_register.md` risks #15-#16.
Full evidence: `integration_lab/evidence/session_recovery_step_c/`.

## What's not implemented yet

`BeliefCutoffPoliceBrain` (the original candidate strategy — only the
from-scratch baseline exists), a live GUI, a visual replay *viewer* (the
headless verifier exists), Gmail reporting, public network exposure, and
league play. A real two-process game/series and the mutual cross-repo audit
**are now implemented and verified** (session recovery step C) — see above.

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
uv run python -m police_peer negotiate-smoke   # IMPLEMENTED (Batch 1) -- requires
                                                 # thief_peer's own negotiate-smoke
                                                 # running too; see
                                                 # integration_lab/run_negotiation_smoke.py
uv run python -m police_peer peer --role police --no-gui   # NOT YET IMPLEMENTED
```

## Third-party attribution

See `THIRD_PARTY_NOTICES.md`. Reused elements are limited to small, attributed
adaptations (a commit-reveal hash shape, a token-bucket formula, an OAuth bootstrap
pattern, a protocol naming convention) — never substantial verbatim code. Full
classification: `integration_lab/audit/reference_reuse_plan.md`.

## Submission tag

Not yet tagged. Will be `v1.0-submission` once `SUBMISSION_READY` (see
`integration_lab/audit/PROGRESS.md` for current readiness level — `LOCAL_READY`
as of session recovery step C; `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY`
not yet reached).

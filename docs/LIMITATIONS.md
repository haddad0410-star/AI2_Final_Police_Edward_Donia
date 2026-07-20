# Limitations — Police Peer

Current, honest state as of this scaffold (Phase 1-2, no application code written):

- No FastMCP server/client exists — nothing here has run over real HTTP yet.
- No game engine, state machine, strategy, scent/belief model, cryptography, GUI,
  replay, or Gmail sender is implemented.
- `pheromone_min_center_intensity=0.5` (seen in the reference repo's config) is not
  confirmed as a binding Appendix F value — tracked as an open item, not assumed.
  See `integration_lab/audit/risk_register.md` risk #2.
- Repository visibility (public vs. private) and its licensing implications are
  unresolved pending your decision — see `integration_lab/audit/manual_gates.md`
  Gate E.
- No league opponent, public network exposure, or Gmail send has occurred.

This file will be kept current every phase — never allowed to go stale while claiming
a higher readiness level than `integration_lab/audit/PROGRESS.md` supports.

## Current state (Implementation Batch 3)

- `BeliefCutoffPoliceBrain` is implemented, unit-tested (22 tests), and
  validated over 3 real six-sub-game HTTP series — but held-out research
  evaluation (100 games) and the real HTTP series both found **no
  demonstrated capture-rate improvement** over `BaselinePoliceBrain` in the
  current experimental configuration (both 0% captures). Root cause: the
  real wire protocol does not currently deliver scent or hint signal to
  either brain's belief update, so belief never concentrates enough for
  the barrier-confidence gate to open — a pre-existing system
  characteristic, not a defect in this batch's strategy code. Full
  analysis: `integration_lab/evidence/batch3/strategy_research/limitations.md`.
- GUI, Gmail reporting, public network exposure, and league play remain
  not implemented/run, unchanged from session recovery step C.
- `pheromone_min_center_intensity=0.5` remains unconfirmed as binding (risk
  #2, unchanged). Repository visibility/licensing consent (Manual Gate E)
  remains unresolved, unchanged.
- Readiness: `LOCAL_READY` (unchanged from session recovery step C — Batch
  3 adds strategy work on top of an already-`LOCAL_READY` local P2P
  baseline; `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY` still not
  claimed).

## Current state (session recovery step C)

- Implemented and independently verified: config loading, domain
  models/board physics, scent/belief, protocol schemas, commit-reveal
  crypto, canonical `declaration/2` Step-0 declaration, state machine,
  deadline tracker, watchdog, baseline strategy brain, template hints,
  sub-game runtime, series runtime, JSON artifact generation, and the
  headless replay verifier.
- **New this step**: a real two-process game/series against the actual
  Thief opponent (one sub-game and a full six-sub-game series, both over
  real FastMCP HTTP), and the mutual cross-repo artifact/audit comparison
  (96/96 checks passed) — both previously unimplemented/unrun, now done.
  Six real cross-repo protocol/wiring defects were found and fixed only by
  actually running two independent processes against each other — see
  `CHANGELOG.md` and `risk_register.md` risks #15-#16.
- **Still not implemented or run**: `BeliefCutoffPoliceBrain` (only the
  from-scratch baseline exists), a live GUI, a replay *viewer* (the
  headless verifier exists; a visual viewer does not), Gmail reporting,
  public network exposure/tunnel, and league play.
- The declaration schema divergence between this repo and the Thief repo
  (risk #14) is **resolved** — canonical `declaration/2`, verified
  byte-identical fixtures.
- `pheromone_min_center_intensity=0.5` remains unconfirmed as binding (risk
  #2, unchanged from Batch 1).
- Repository visibility/licensing consent (Manual Gate E) remains
  unresolved, unchanged from Batch 1.
- Readiness: `LOCAL_READY` (session recovery step C). `NETWORK_READY`/
  `LEAGUE_READY`/`SUBMISSION_READY` not claimed.

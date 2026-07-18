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

## Current state (session recovery step B)

- Implemented and independently verified: config loading, domain
  models/board physics, scent/belief, protocol schemas, commit-reveal
  crypto, Step-0 declaration, state machine, deadline tracker, watchdog,
  baseline strategy brain, template hints, sub-game runtime, series runtime,
  JSON artifact generation (now wired into the CLI), and the headless replay
  verifier.
- **Still not implemented or run**: `BeliefCutoffPoliceBrain` (only the
  from-scratch baseline exists), a live GUI, a replay *viewer* (the
  headless verifier exists; a visual viewer does not), Gmail reporting, a
  real two-process game/series against an actual opponent, the mutual
  cross-repo audit, public network exposure/tunnel, and league play.
- A genuine, pre-existing schema divergence between this repo's and the
  Thief repo's Step-0 declaration (field names and hardware-field shape)
  was found this session via serialized fixture comparison and is
  unresolved — see `integration_lab/audit/risk_register.md` risk #14. It
  will block a byte-level declaration exchange until resolved.
- `pheromone_min_center_intensity=0.5` remains unconfirmed as binding (risk
  #2, unchanged from Batch 1).
- Repository visibility/licensing consent (Manual Gate E) remains
  unresolved, unchanged from Batch 1.

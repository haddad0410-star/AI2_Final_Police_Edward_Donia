# Protocol — Police Peer (role-local summary)

**Canonical source:** `integration_lab/audit/protocol_contract.md`. This file
summarizes only what's specific to running this repo as the Police side.

- This peer's default local port: `8901` (private, set in `config/police/game.toml`, not negotiated).
- Opponent URL: supplied via this peer's own `game.toml` / `.env` (`OPPONENT_MCP_URL`) —
  the only network detail this peer is given about the opponent.
- Tool surface exposed by this peer's FastMCP server: `negotiate`, `receive_turn`,
  `submit_audit`, `receive_control` (see canonical doc for exact schemas). **Batch 1
  implements only `health`, `negotiate`, and `propose_config`** (real HTTP, see
  `src/police_peer/infrastructure/mcp_server.py`) — `receive_turn`/`submit_audit`/
  `receive_control` are schemas only (`src/police_peer/protocol/`), not yet wired to
  server tools; that is a later batch. See `docs/adr/ADR-0012-receive-move-alias-
  assessment.md` for the `receive_move` alias decision.
- Police-specific wire fields: `capture_claim` (this side sends it), `barrier_placed` (this side sends it, publicly and truthfully).
- Four JSON artifacts this peer writes each series: `declaration_<game_id>.json`,
  `config_<game_id>_g<NN>.json` (x6), `log_<game_id>_g<NN>.json` (x6),
  `result_<game_id>.json`. Implemented (Batch 2, Phase 11) and, as of
  session recovery step B, wired into `run-series --artifacts-dir`; verified
  byte-identical in schema to the independently-built Thief repo's
  artifacts via serialized fixture comparison — see
  `integration_lab/evidence/session_recovery_step_b/feature_parity.md`.
  The Step-0 declaration schema is now frozen and cross-repo-compatible as
  canonical `declaration/2` (session recovery step C, Task 2 — see
  `docs/schemas/declaration.schema.json`, `protocol_contract.md` §3.4a, and
  `risk_register.md` risk #14, now resolved).
- Real two-process negotiation evidence: `integration_lab/evidence/negotiation_smoke/`
  (actual stdout/stderr/exit codes from two independently-launched OS processes).
  A real two-process full game/series has NOT been run yet (explicitly out
  of scope through session recovery step B).

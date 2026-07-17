# Protocol — Police Peer (role-local summary)

**Canonical source:** `integration_lab/audit/protocol_contract.md`. This file
summarizes only what's specific to running this repo as the Police side.

- This peer's default local port: `8901` (private, set in `config/police/game.toml`, not negotiated).
- Opponent URL: supplied via this peer's own `game.toml` / `.env` (`OPPONENT_MCP_URL`) —
  the only network detail this peer is given about the opponent.
- Tool surface exposed by this peer's FastMCP server: `negotiate`, `receive_turn`,
  `submit_audit`, `receive_control` (see canonical doc for exact schemas — none of this
  is implemented yet in this scaffold).
- Police-specific wire fields: `capture_claim` (this side sends it), `barrier_placed` (this side sends it, publicly and truthfully).
- Four JSON artifacts this peer writes each series: `declaration_<game_id>.json`,
  `config_<game_id>_g<NN>.json` (x6), `log_<game_id>_g<NN>.json` (x6),
  `result_<game_id>.json`.

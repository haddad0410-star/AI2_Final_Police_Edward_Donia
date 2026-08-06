# Protocol — Police Peer (role-local summary)

**Canonical source:** `_post4b_supplementary_evidence/audit/protocol_contract.md`. This file
summarizes only what's specific to running this repo as the Police side.

- This peer's default local port: `8901` (private, set in `config/police/game.toml`, not negotiated).
- Opponent URL: supplied via this peer's own `game.toml` / `.env` (`OPPONENT_MCP_URL`) —
  the only network detail this peer is given about the opponent.
- Tool surface exposed by this peer's FastMCP server: `health`, `negotiate`,
  `propose_config`, `receive_turn` (plus a `receive_move` compatibility alias),
  `submit_audit`, `receive_control` — all real FastMCP HTTP tools, all wired
  and used in real gameplay (`src/police_peer/infrastructure/mcp_server.py`).
  See `docs/adr/ADR-0012-receive-move-alias-assessment.md` for the
  `receive_move` alias decision.
- Police-specific wire fields: `capture_claim` (this side sends it), `barrier_placed` (this side sends it, publicly and truthfully).
- Four JSON artifacts this peer writes each series: `declaration_<game_id>.json`,
  `config_<game_id>_g<NN>.json` (x6), `log_<game_id>_g<NN>.json` (x6),
  `result_<game_id>.json`. Implemented (Batch 2, Phase 11) and, as of
  session recovery step B, wired into `run-series --artifacts-dir`; verified
  byte-identical in schema to the independently-built Thief repo's
  artifacts via serialized fixture comparison (raw evidence produced
  during development in the full project workspace; not included in this
  single-repo package).
  The Step-0 declaration schema is now frozen and cross-repo-compatible as
  canonical `declaration/2` (session recovery step C, Task 2 — see
  `docs/schemas/declaration.schema.json`, `protocol_contract.md` §3.4a, and
  `risk_register.md` risk #14, now resolved).
- Real two-process negotiation evidence (actual stdout/stderr/exit codes
  from two independently-launched OS processes), and since then several
  real two-process six-sub-game HTTP series (advanced vs advanced, both
  replay verifiers reporting `VERIFIED`/`FULL_BILATERAL_VERIFICATION=true`),
  were produced during development in the full project workspace and are
  not included in this single-repo package.

**Note:** this section has been updated past its original Batch-1-era scope;
see `_post4b_supplementary_evidence/audit/PROGRESS.md` for the current
readiness record.

**Scent field-name correction (Batch 3.6 Task 2):** `protocol_contract.md`
§3.2's `scent_grid` field name is this project's own paraphrase of the
book's prose description of the sealed record — a full-text search of the
book PDF found no literal `scent_grid`/`smell_grid` field name anywhere.
The underlying semantics (full-board cumulative decaying trail, sealed raw
values not a digest) are still correctly implemented; only the exact
identifier is ours. (Book-citation audit produced during development in
the full project workspace; not included in this single-repo package.)

**Sealed-record schema unified as `commitment/1` (Batch 4B):** the sealed
turn payload's field set is now identical in both repos (17 canonical
fields, `domain/crypto/payload.py::CANONICAL_FIELD_SET`), replacing the
prior per-repo `commit-reveal/2`/`sealed-turn/2` shapes that diverged in
two mechanical ways (this repo's nested `state` dict vs. the opponent's
opaque digest string; `config_sha256` placement). This is what makes
genuine bilateral commitment verification possible — see
`_post4b_supplementary_evidence/batch4b/commitment_schema_audit.md` and
`docs/SECURITY.md`'s Batch 4B section. `protocol_contract.md` should be
updated to reference `commitment/1` as the current binding sealed-record
schema once both groups' contract is renegotiated with a real opponent;
until then this is a same-project-internal schema unification, not yet a
cross-team-negotiated protocol change.

**Gate A1 -- optional transport-level bearer auth (`--public` mode only):**
when this peer or the opponent runs with `--public`, every HTTP request to
that peer must carry `Authorization: Bearer <its own PUBLIC_BIND_TOKEN>`,
verified by `infrastructure/auth_middleware.py` before any tool dispatch.
This is a transport-level addition, not a change to any message schema or
tool argument shape -- ordinary localhost self-play (no `--public`) is
completely unaffected, and the header is added by the *caller* (via
`OPPONENT_MCP_TOKEN`, see `docs/PUBLIC_NETWORK_SETUP.md`), never embedded
in a message body. See `docs/SECURITY.md`'s Gate A1 section for the full
implementation.

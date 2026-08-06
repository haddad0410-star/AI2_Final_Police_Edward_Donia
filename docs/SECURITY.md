# Security — Police Peer

## Threat model summary

Full detail: `_post4b_supplementary_evidence/audit/risk_register.md` and (once written)
`reports/threat_model.md`. Core adversarial assumption per the book (Ch.5.2): the
opponent may attempt to rewrite history, deny a committed move, or lie about a
capture/win claim. Defense: SHA-256 commit-reveal (book Ch.5.3) plus a mutual
end-of-game audit that recomputes every hash.

## Secrets handling

- `credentials.json` / `token.json` live outside this repository, path supplied via
  `GOOGLE_OAUTH_CREDENTIAL_DIR` (see `.env-example`).
- `.gitignore` blocks `.env`, `credentials.json`, `token.json`, `client_secret*.json`.
- `security_scan.py` (implemented, Batch 1; lives in the multi-repo
  development workspace, not included in this single-repo package) asserts
  none of these are present/tracked, scans for API-key-like patterns,
  hardcoded Windows paths, reference-repo group identities, hardcoded
  paid-model-provider defaults, and a wrong `num_games` in the real league
  config. Most recently re-run and recorded clean
  (`"clean": true`, no findings) in item 16 of
  `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`.
- `verify_isolation.py` (implemented, Batch 1; same development workspace,
  not included in this single-repo package) asserts no cross-repo imports,
  no cross-repo config paths, no opponent-true-position field names, and no
  shared-state module hints. Most recently re-run and recorded clean
  (`"isolated": true`, no violations) in item 15 of
  `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`.

## Batch 1 protocol-schema validation (implemented)

Every message category (health, declaration, config proposal, negotiation ack, turn
commitment, turn reveal, public turn envelope, hint, scent payload, barrier
declaration, capture claim/response, audit submission, control, protocol error) has
strict `__post_init__` validation and negative tests — 23 tests in
`tests/protocol/test_protocol_schemas.py`. This validates message *shape*; the
commit-reveal *lifecycle* itself is implemented and tested separately (see below).

## Security test categories (`tests/security/`) — implemented

- Tamper injection: alter move, hint, verdict, nonce, step, config, capture answer,
  record order — each is detected by the audit
  (`tests/security/test_commit_reveal.py`, `tests/security/test_replay_verifier.py`).
- Nonce reuse rejection (`test_nonce_reuse_detected_by_audit`).
- Constant-time comparison on reveal verification, no timing side-channel
  (`test_constant_time_compare_is_actually_used`).
- False capture-claim / false win-claim detection (covered across
  `tests/protocol/test_protocol_schemas.py`, `tests/unit/test_turn_router.py`, and
  `tests/unit/test_artifacts.py`, in addition to the commit-reveal audit tests above).

Commit-reveal is fully implemented, not schema-only — sealing, acknowledgment,
reveal, and audit recomputation all run in real gameplay
(`src/police_peer/protocol/messages_turn.py`, `messages_capture.py`,
`domain/crypto/`), unified under the `commitment/1` schema (see the Batch 4B
section below).

## Session recovery step B additions

- **Production resource-leak fix**: `infrastructure/server_lifecycle.py`'s
  shutdown path previously relied on `asyncio.Task.cancel()`, which does
  not reliably close the underlying Uvicorn listening socket (verified by
  direct experiment) — a real, if low-severity, resource leak in
  production. Replaced with a `ManagedServer` class doing a genuinely
  graceful shutdown; see the CHANGELOG (raw evidence produced during
  development in the full project workspace; not included in this
  single-repo package).
- **Replay-verifier hardening**: the headless replay verifier (Phase 12)
  could not detect a duplicate/relabeled sub-game record (two artifact
  files, different names, claiming the same `sub_game_number` internally)
  — a naive number-keyed lookup silently kept only the last one. Fixed with
  `_check_no_duplicate_sub_games`; regression test added.
- The above two items and the Phase 10-12 tamper-detection test suite
  (commit-reveal audit, nonce reuse, sequence ordering, barrier/capture
  bounds, score recomputation, config-hash/game_uid consistency) are all
  now implemented, tested, and independently re-verified (raw evidence
  produced during development in the full project workspace; not included
  in this single-repo package).
  Still not done: a real cross-process tamper drill against an actual
  opponent, or the mutual audit.

## Session recovery step C additions

- **Declaration schema hardened (Task 2, resolves risk #14)**: the Step-0
  declaration is now parsed via a strict allow-list (`declaration_parsing.py`
  ::`parse_declaration`) — any unrecognized top-level or `hardware` field is
  rejected outright (`SchemaValidationError`), never silently accepted.
  `declaration/1`-era aliases (`commit_hash`, `config_sha256`) are accepted
  on input only, normalized immediately, and rejected as ambiguous if
  present alongside a differing canonical value — closing a path where a
  malformed/legacy declaration could otherwise be misread. A new
  `content_sha256` commitment field (`canonical_sha256_hex` over every other
  field) gives the replay verifier an additional, independently-recomputable
  integrity check beyond the existing nonce-based seal/verify exchange.
  Cross-repo compatibility (not a security boundary by itself, but a
  precondition for any real declaration exchange) verified by
  `compare_declaration_schemas.py` (development-workspace script, not
  included in this single-repo package; original Session-recovery-step-C
  evidence likewise produced during development and not included here).
  Most recently re-run and recorded PASS (schema files byte-identical,
  16/16 non-intrinsic declaration fields match exactly) in item 18 of
  `_post4b_supplementary_evidence/post4b_finalization/FINAL_LOCAL_AUDIT.md`.

## Batch 4A additions

- **Gmail credential isolation** (`infrastructure/gmail_credentials.py`):
  `credentials.json`/`token.json` resolved only via
  `GOOGLE_OAUTH_CREDENTIAL_DIR` (env var, never a config field); scope
  enforcement (`gmail.send` only, rejects `.modify`/`.compose`/`.readonly`/
  full-mailbox) happens in code before any network call; error messages
  never echo file content. 12 tests
  (`tests/security/test_gmail_credentials.py`), including a real check
  that no `credentials.json`/`token.json`/`client_secret*` file is ever
  tracked by git.
- **Gmail Gatekeeper** (`infrastructure/gmail_gatekeeper.py`): bounded
  retries (never an infinite loop), a per-attempt timeout, a queue-depth
  cap, and idempotency-key-based duplicate-send suppression — 10 tests,
  always against a mocked send function.
- **Report-refusal on unverified evidence**: the Gmail reporter runs the
  real, unmodified replay verifier on target artifacts before building
  any report and refuses (does not silently proceed) if they are not
  `VERIFIED` — `sdk/report_runner.py`, tested
  (`tests/unit/test_report_runner.py`).
- **Public-network bearer-token auth** (`infrastructure/public_auth.py`):
  env-var-only (`PUBLIC_BIND_TOKEN`) token source, constant-time
  comparison (`hmac.compare_digest`), never logged. 7 tests
  (`tests/security/test_public_auth.py`). The server's existing
  localhost-only bind guard (`infrastructure/server_lifecycle.py`) is
  unchanged — this module is prepared but not wired into the live server.
- **Live GUI opponent-position-leak scanner**
  (`tests/unit/test_gui_no_opponent_leak.py`): reflection-based, fails
  the build if any GUI-reachable dataclass grows a field shaped like
  `opponent_true_position`.
- **Replay-viewer cross-schema finding**: this repo's own replay verifier
  cannot correctly recompute the opponent's differently-shaped commitment
  hashes — see `docs/LIMITATIONS.md`'s Batch 4A section for the full
  explanation and fix (never claim a verdict this repo cannot actually
  compute).

## Batch 4B additions — bilateral commitment verification (resolves the
## Batch 4A cross-schema finding above)

- **Root cause, precisely identified**: the Batch 4A finding traced to two
  narrow, mechanical field-shape divergences, not an inherent consequence
  of independent implementation — this repo's `state` field was a nested
  dict (`{"position": [...], "config_sha256": ...}`) while Thief's was an
  opaque digest string, and `config_sha256` was nested inside `state` here
  but a genuine top-level field in Thief. 14 of ~16 payload fields already
  had identical shape. Both repos' canonical-JSON encoders were already
  byte-identical. Full field-by-field audit:
  `_post4b_supplementary_evidence/batch4b/commitment_schema_audit.md`.
- **Canonical schema unified** (`domain/crypto/payload.py`,
  `SCHEMA_VERSION = "commitment/1"`): `state` replaced by a flat
  `position` tuple field; `config_sha256` promoted to a real top-level
  field. `CANONICAL_FIELD_SET` (17 keys) is now identical in both repos.
  `to_canonical_dict()` is schema-version-aware — legacy
  `commit-reveal/1`/`/2` records still canonicalize to their EXACT
  original shape, so all Batch 1-4A evidence remains self-verifiable
  without rewriting any file on disk.
- **Real bilateral verification, not just a shared schema on paper**:
  because the field SET is now unified, this repo's EXISTING,
  already-tested verification pipeline (`services/replay_verifier.py`,
  `replay_checks.py`) correctly recomputes and verifies a genuine Thief
  `commitment/1` record too — confirmed by 10 byte-identical cross-repo
  test vectors (`_post4b_supplementary_evidence/batch4b/test_vectors/`), a
  21-category bilateral tamper matrix where BOTH repos' own verifiers
  independently detect every mutation
  (`_post4b_supplementary_evidence/batch4b/tamper_matrix/`, `all_detected=true`),
  and a real six-sub-game two-process FastMCP series where both sides'
  `replay` command reports `FULL_BILATERAL_VERIFICATION=true`
  (`_post4b_supplementary_evidence/batch4b/bilateral_series/`). This repo never
  imports `thief_peer`; it only calls its own crypto/verifier on
  whichever directory it's given (`services/bilateral_verify.py`).
- **New role-consistency and unknown-field checks**
  (`replay_checks.py::_check_role_fields`/`_check_unknown_fields`): a
  Police record carrying a Thief-only `claim_response`/`win_claim` value
  (or vice versa), or any `commitment/1` record carrying a field outside
  the canonical set, is now flagged as tampered — closing a class of
  forgery the schema-shape fix alone would not have caught.
- **Real bug found and fixed via the tamper matrix**:
  `domain/crypto/audit.py::_check_sequence_contiguous` had deliberately
  tolerated step reordering (only gaps were checked) — an asymmetry
  against Thief's own `steps_in_order` check, which does reject
  reordering. Since tolerating a real tamper class is a weaker posture,
  not a design choice this batch should preserve, the check was
  strengthened to also reject reveal order that does not match step
  order; verified via the bilateral tamper matrix's `record_ordering`
  category (now `DETECTED` by both repos, was `MISSED` by this repo
  before the fix).
- **Gmail bilateral gate** (`sdk/report_runner.py`, Task 9): `report
  --opponent-artifacts-dir <dir>` gates report construction (dry-run AND
  `--send`) on full bilateral verification via
  `services/bilateral_verify.py`, not merely this side's own
  `verify_replay`. Real evidence, both accept and refuse paths:
  `_post4b_supplementary_evidence/batch4b/gmail_bilateral_gate/`.

## Post-Batch-4B additions — narrow `McpError` connectivity classification

- **`infrastructure/mcp_client.py`**: a client-side session-initialize
  timeout (raised by the installed `mcp`/`fastmcp` packages as `McpError`)
  is now reclassified as `PeerUnavailableError` — but ONLY when
  `error.code == httpx.codes.REQUEST_TIMEOUT`, the exact code used by the
  only 2 client-side-timeout raise sites in the installed packages
  (verified directly against `mcp/shared/session.py` and
  `fastmcp/utilities/exceptions.py` before writing the fix). Every other
  `McpError` — a genuine remote/application error, including the
  opponent's own real JSON-RPC error forwarded verbatim — still
  propagates unchanged; this is deliberately NOT a blanket
  `except McpError`/`except Exception`. `tests/unit/test_mcp_client.py`
  proves both the narrow reclassification and that non-timeout errors are
  never swallowed.

## Gate A1 additions — local public-endpoint auth + rate-limit implementation

- **`infrastructure/auth_middleware.py`**: `BearerAuthMiddleware`, a raw
  ASGI middleware enforcing `Authorization: Bearer <PUBLIC_BIND_TOKEN>` on
  every HTTP request, applied via `FastMCP.http_app(middleware=...)` --
  before FastMCP's own routing/tool dispatch, never inside an individual
  `@mcp.tool` (so a rejected request can never invoke one). Constant-time
  comparison (`hmac.compare_digest`, verified by
  `tests/unit/test_auth_middleware_constant_time.py` spying on the real
  call, not a timing measurement). The rejection reason is one of a fixed
  small set of words -- never the presented or expected token, in the
  response, an exception, or anywhere else
  (`tests/unit/test_auth_middleware.py`).
- **`services/incoming_gatekeeper.py`**: `IncomingGatekeeper` bounds
  concurrent in-flight operations (semaphore) and the rolling per-minute
  rate (sliding window), config-driven from the existing `rate_limits.json`
  top-level block (30/min, 2 concurrent, queue 100), independent of the
  Gmail sender's own `Gatekeeper` (no shared mutable state). Cancellation,
  an exception, or a timeout inside an admitted slot all still release it
  (`tests/unit/test_incoming_gatekeeper.py`).
- **`sdk/public_mode.py`**: `resolve_public_tokens()` fails closed --
  `--public` with no (or a blank) `PUBLIC_BIND_TOKEN` refuses to start,
  never falls back to unauthenticated mode. `_ALLOWED_LOCAL_HOSTS`
  (`server_lifecycle.py`) is completely untouched by any of this --
  `--public` only changes whether middleware is attached, never what host
  is bound.
- **`infrastructure/mcp_client.py`**: adds `Authorization: Bearer <token>`
  via `fastmcp.client.auth.bearer.BearerAuth` (backed by `pydantic.SecretStr`,
  so it can't leak via a plain `repr()`) only when a token is given; a
  local/no-token call is byte-for-byte the same request it always was
  (`tests/unit/test_mcp_client_token.py`).

## Gate A1 correction — logical-operation rate limiting, not raw HTTP

The original Gate A1 rate limiter was ASGI-level, so it counted every raw
HTTP request FastMCP's streamable-HTTP transport happens to use underneath
one logical call (session initialize, `notifications/initialized`,
capability discovery, the real `tools/call`, session teardown -- roughly
6 raw requests per call). Appendix F Table 19's "30 requests per minute"
binding minimum is a logical-operation budget (the table's own worked
context, per this project's `rate_limits.json`, is an outbound API-call
Gatekeeper), so counting raw transport frames against it made the
committed 30/min config unable to sustain even light real gameplay --
discovered only by actually running a real authenticated two-process
series, not by any unit or single-server integration test.

- **`infrastructure/mcp_rate_limit_middleware.py`**: `McpRateLimitMiddleware`,
  a FastMCP protocol-level middleware (`Middleware.on_call_tool`,
  registered via `FastMCP.add_middleware` -- NOT the ASGI
  `http_app(middleware=...)` list) charges exactly one `IncomingGatekeeper`
  slot per real `tools/call` dispatch, before the tool body runs
  (`tests/unit/test_mcp_rate_limit_middleware.py`,
  `tests/integration/test_public_mode_http.py`). `health` is excluded
  (liveness/readiness probe, not a logical game operation). Auth stays
  ASGI-level, unchanged -- it must guard session establishment itself.
- **`infrastructure/outbound_pacer.py`**: `OutboundPacer` proactively
  WAITS (never rejects) for a rate/concurrency slot before an outbound call
  to a `--public` opponent, so a compliant client paces itself under the
  same binding minimums rather than bursting and relying on repeated
  overload responses (`tests/unit/test_outbound_pacer.py`). Only
  constructed when an opponent token is known (i.e. the opponent runs
  `--public`); ordinary local self-play never builds one
  (`tests/unit/test_pacer_gating.py`).
- **`infrastructure/mcp_client.py`**: a real overload response
  (`McpOverloadError`, a distinct JSON-RPC error code) is retried, honoring
  the server's own `retry_after_seconds` hint, up to `DEFAULT_MAX_RETRIES`
  (3 -- Table 19's binding minimum retry count) times, then becomes an
  ordinary `PeerUnavailableError` -- never retried indefinitely
  (`tests/unit/test_mcp_client_retry_backoff.py`).
- Real, real-HTTP proof (not just unit-level): `tests/integration/test_public_mode_http.py`
  (missing/wrong/correct token, one logical call charges the budget exactly
  once despite ~6 raw HTTP requests underneath, excess logical calls
  rejected before the tool runs, `health` never charged, auth rejection
  never charged, max-2-concurrent, still-127.0.0.1-only bind) and
  `tests/integration/test_public_mode_lifecycle.py` (repeated start/stop
  releases the same port, still no orphans). All of these run against
  `127.0.0.1` only, in-process -- no tunnel, no public exposure.

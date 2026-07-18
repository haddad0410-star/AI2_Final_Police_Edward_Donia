# Security — Police Peer

## Threat model summary

Full detail: `integration_lab/audit/risk_register.md` and (once written)
`reports/threat_model.md`. Core adversarial assumption per the book (Ch.5.2): the
opponent may attempt to rewrite history, deny a committed move, or lie about a
capture/win claim. Defense: SHA-256 commit-reveal (book Ch.5.3) plus a mutual
end-of-game audit that recomputes every hash.

## Secrets handling

- `credentials.json` / `token.json` live outside this repository, path supplied via
  `GMAIL_CREDENTIALS_DIR` (see `.env-example`).
- `.gitignore` blocks `.env`, `credentials.json`, `token.json`, `client_secret*.json`.
- `integration_lab/security_scan.py` (implemented, Batch 1) asserts none of these are
  present/tracked, scans for API-key-like patterns, hardcoded Windows paths, reference-
  repo group identities, hardcoded paid-model-provider defaults, and a wrong
  `num_games` in the real league config. Real output (clean):
  `integration_lab/evidence/security_scan_output.json`.
- `integration_lab/verify_isolation.py` (implemented, Batch 1) asserts no cross-repo
  imports, no cross-repo config paths, no opponent-true-position field names, and no
  shared-state module hints. Real output (clean):
  `integration_lab/evidence/verify_isolation_output.json`.

## Batch 1 protocol-schema validation (implemented)

Every message category (health, declaration, config proposal, negotiation ack, turn
commitment, turn reveal, public turn envelope, hint, scent payload, barrier
declaration, capture claim/response, audit submission, control, protocol error) has
strict `__post_init__` validation and negative tests — 23 tests in
`tests/protocol/test_protocol_schemas.py`. This validates message *shape*; it does not
yet implement the commit-reveal *lifecycle* (see below).

## Planned security test categories (`tests/security/`) — later batch

- Tamper injection: alter move, hint, verdict, nonce, step, config, capture answer,
  record order — each must be detected by the audit.
- Nonce reuse rejection.
- Constant-time comparison on reveal verification (no timing side-channel).
- False capture-claim / false win-claim detection.

None of these lifecycle tests exist yet — commit-reveal is schema-only this batch
(`src/police_peer/protocol/messages_turn.py`, `messages_capture.py`); the full sealing/
audit implementation is a later batch. This document will be updated again then.

## Session recovery step B additions

- **Production resource-leak fix**: `infrastructure/server_lifecycle.py`'s
  shutdown path previously relied on `asyncio.Task.cancel()`, which does
  not reliably close the underlying Uvicorn listening socket (verified by
  direct experiment) — a real, if low-severity, resource leak in
  production. Replaced with a `ManagedServer` class doing a genuinely
  graceful shutdown; see the CHANGELOG and `integration_lab/evidence/
  session_recovery_step_b/server_lifecycle/`.
- **Replay-verifier hardening**: the headless replay verifier (Phase 12)
  could not detect a duplicate/relabeled sub-game record (two artifact
  files, different names, claiming the same `sub_game_number` internally)
  — a naive number-keyed lookup silently kept only the last one. Fixed with
  `_check_no_duplicate_sub_games`; regression test added.
- The above two items and the Phase 10-12 tamper-detection test suite
  (commit-reveal audit, nonce reuse, sequence ordering, barrier/capture
  bounds, score recomputation, config-hash/game_uid consistency) are all
  now implemented, tested, and independently re-verified — see
  `integration_lab/evidence/session_recovery_step_b/police_phase_10_12/`.
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
  `integration_lab/scripts/compare_declaration_schemas.py`; see
  `integration_lab/evidence/session_recovery_step_c/task2_declaration_schema/`.

# Gmail Reporting — Police Peer

**Status (Batch 4A): implemented and tested in dry-run; `--send` exists in
code but has never been invoked.** No OAuth flow has ever been run by
Claude; no real Gmail API call has ever been made.

## Binding requirements

- **Scope: `gmail.send` only.** Confirmed by Appendix A's explicit "Least Privilege"
  callout (printed p.107) and cross-checked against the general Google API guide's
  broader `gmail.modify`+`calendar` demo scopes, which are **not** used here — see
  `integration_lab/audit/risk_register.md` risk #11 and
  `integration_lab/audit/manual_gates.md` Gate G. Enforced in code, not just
  documented: `infrastructure/gmail_credentials.py::assert_scope_is_send_only`
  rejects `gmail.modify`/`.compose`/`.readonly`/`https://mail.google.com/`
  before any network call is made (tested,
  `tests/security/test_gmail_credentials.py`).
- **Recipient: `rmisegal+uoh26finalgame@gmail.com`** (Appendix F Table 20, visually
  confirmed character-by-character — not the HW6 address). Enforced in code:
  `infrastructure/gmail_sender.py` raises `RecipientMismatchError` on any
  other recipient value, before any network call.
- **Credentials location:** `credentials.json` + `token.json` live outside this repo,
  path via the `GOOGLE_OAUTH_CREDENTIAL_DIR` env var. Never logged, never
  committed, never printed by any script — see
  `infrastructure/gmail_credentials.py` and
  `tests/security/test_gmail_credentials.py` (12 tests, including
  "error messages never contain file content" and "no credential content
  logged").

## Modes

- **`dry-run` (default)** — `uv run python -m police_peer report --artifacts-dir <dir>`.
  Builds and prints the real structured report JSON from real artifact
  files. No network call, no OAuth. Always available, always safe.
- **`send`** — `... report --artifacts-dir <dir> --send`. Requires
  `GOOGLE_OAUTH_CREDENTIAL_DIR` to point at real, valid credential files,
  AND your prior explicit approval each time (Manual Gate C). Routes
  through the real `Gatekeeper` (rate limit/concurrency/retry/idempotency).
  **Never invoked by Claude in this batch.**
- **No `draft` mode.** Removed from this plan: drafting requires a
  broader Gmail scope than pure sending, which would violate the
  least-privilege mandate above.

## Report format

Structured JSON only (book Ch.9.3.3), never free text.
`domain/gmail_report_schema.py::build_report` produces:
`schema_version`, `recipient`, `game_id`/`game_uid`, `group_id`, `members`,
both repositories, both MCP URLs, `sub_game_outcomes`, `scores`,
`aggregate_result`, `audit_status`, `config_sha256`, this side's
`commit_hashes`, `hardware_declaration`, `strategy_class`, `token_usage`,
`runtime_summary`, and SHA-256 `artifact_hashes` for every input file.
Every value traces back to an already-written, already-public artifact
file — nothing is invented. Never includes credentials, OAuth tokens,
bearer tokens, private TOML, or unrevealed secrets (tested,
`tests/unit/test_gmail_report_schema.py::test_report_never_includes_credentials_or_secrets`).

## Refusal on unverified evidence

`sdk/report_runner.py::build_report_from_artifacts` runs the real,
unmodified `services/replay_verifier.py::verify_replay` on the target
artifacts FIRST and raises `ReportRefusedError` (CLI exit code 3) if they
are not `VERIFIED` — a report is never built, let alone sent, from
tampered or incomplete evidence. Tested:
`tests/unit/test_report_runner.py`; real demonstration:
`integration_lab/evidence/batch4a/gmail_dry_run/invalid_report_rejection.json`.

### Batch 4B: bilateral verification gate

`report --artifacts-dir <own> --opponent-artifacts-dir <opponent>` (both
`report` and `report --send`) gates on FULL BILATERAL verification via
`services/bilateral_verify.py::verify_bilateral` instead of the
single-sided check above — both sides must be independently verified AND
both `VERIFIED`, not just this side's own artifacts. Without
`--opponent-artifacts-dir`, the single-sided gate above still applies
(strictly more conservative, never less). Real evidence (accept and
refuse paths, real bilateral series from Task 7):
`integration_lab/evidence/batch4b/gmail_bilateral_gate/`. Tested:
`tests/unit/test_report_runner.py::test_bilateral_gate_*`.

## Rate limiting (Gatekeeper)

`infrastructure/gmail_gatekeeper.py::Gatekeeper`, built on the existing
private `rate_limits.json`/`RateLimitsConfig` (Appendix F Table 19
minimums): token-bucket requests-per-minute limit, concurrency semaphore,
bounded retries with backoff on HTTP 429, a queue-depth limit, a
per-attempt timeout, and idempotency-key-based duplicate-report
suppression. 10 tests, always against a mocked send function — never a
real Gmail API call. Evidence: `integration_lab/evidence/batch4a/gmail_dry_run/rate_limit_test.txt`.

## Dry-run evidence

`integration_lab/evidence/batch4a/gmail_dry_run/`: real report bodies for
a one-sub-game result, a six-sub-game result, and a technical-loss
result, plus the invalid-artifact-refusal, schema-validation, rate-limit,
and security test outputs.

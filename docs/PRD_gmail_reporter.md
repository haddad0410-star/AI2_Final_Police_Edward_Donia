# PRD gmail reporter

## Purpose

Define the automated Gmail reporting tool.

## Requirements

- Scope `gmail.send` only (Appendix A, visually confirmed p.107-108).
- Recipient `rmisegal+uoh26finalgame@gmail.com` (Appendix F Table 20, visually confirmed).
- Credentials outside the repo via `GOOGLE_OAUTH_CREDENTIAL_DIR`.
- Modes: dry-run (default), draft, send (`--send`, requires your explicit approval each time — Manual Gate C).
- Report body is structured JSON, attached, not free text (Ch.9.3.3).

## Acceptance criteria (measurable)

- [x] Dry-run mode produces a valid report JSON without any network call — `tests/unit/test_gmail_sender.py::test_dry_run_never_touches_network`.
- [x] A test with mocked Gmail client proves draft/send code paths work without touching a real account — `tests/unit/test_gmail_gatekeeper.py`, `tests/unit/test_gmail_sender.py` (always against a mocked send function).
- [x] Missing OAuth files produce a clear error, not a silent failure — `tests/security/test_gmail_credentials.py::test_missing_env_var_fails_clearly`, `::test_missing_external_directory_fails_clearly`, `::test_missing_token_file_fails_clearly`.

## Out of scope (for now)

Real send/draft execution (never run unattended — Manual Gate C).

Status: implemented and tested (dry-run, draft, and mocked-send code paths all
exercised for real). Real `--send` delivery to a live Gmail account has never
been invoked and remains gated behind Manual Gate C (OAuth consent + your
explicit send approval each time) — that gate is genuinely still open. See
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

# PRD gmail reporter

## Purpose

Define the automated Gmail reporting tool.

## Requirements

- Scope `gmail.send` only (Appendix A, visually confirmed p.107-108).
- Recipient `rmisegal+uoh26finalgame@gmail.com` (Appendix F Table 20, visually confirmed).
- Credentials outside the repo via `GMAIL_CREDENTIALS_DIR`.
- Modes: dry-run (default), draft, send (`--send`, requires your explicit approval each time — Manual Gate C).
- Report body is structured JSON, attached, not free text (Ch.9.3.3).

## Acceptance criteria (measurable)

- [ ] Dry-run mode produces a valid report JSON without any network call.
- [ ] A test with mocked Gmail client proves draft/send code paths work without touching a real account.
- [ ] Missing OAuth files produce a clear error, not a silent failure.

## Out of scope (for now)

Real send/draft execution (never run unattended — Manual Gate C).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

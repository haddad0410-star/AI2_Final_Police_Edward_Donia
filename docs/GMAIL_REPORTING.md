# Gmail Reporting — Police Peer

## Binding requirements

- **Scope: `gmail.send` only.** Confirmed by Appendix A's explicit "Least Privilege"
  callout (printed p.107) and cross-checked against the general Google API guide's
  broader `gmail.modify`+`calendar` demo scopes, which are **not** used here — see
  `integration_lab/audit/risk_register.md` risk #11 and
  `integration_lab/audit/manual_gates.md` Gate G.
- **Recipient: `rmisegal+uoh26finalgame@gmail.com`** (Appendix F Table 20, visually
  confirmed character-by-character — not the HW6 address).
- **Credentials location:** `credentials.json` + `token.json` live outside this repo,
  path via `GMAIL_CREDENTIALS_DIR` env var. Never logged, never committed.

## Modes

- `dry-run` (default) — builds the report JSON, does not contact Gmail at all.
- `draft` — creates a Gmail draft, does not send.
- `send` — requires an explicit `--send` flag AND your prior approval each time
  (Manual Gate C). Claude will not run this mode unattended.

## Report format

Structured JSON only (book Ch.9.3.3), attached to the email, not pasted as free text.
Schema TBD in `PRD_gmail_reporter.md`, implemented in Phase 12.

Not implemented yet.

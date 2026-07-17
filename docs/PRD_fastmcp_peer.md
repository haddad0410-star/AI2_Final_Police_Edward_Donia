# PRD fastmcp peer

## Purpose

Define this peer's FastMCP server+client responsibilities.

## Requirements

- Real HTTP transport (`transport="http"`), never an in-process mock in production code.
- Tool surface: `negotiate`, `receive_turn`, `submit_audit`, `receive_control` (see `integration_lab/audit/protocol_contract.md`).
- This peer is simultaneously server and client (book Ch.2, Fig.2 symmetric architecture, visually confirmed).
- No central referee; no shared state with the opponent process.

## Acceptance criteria (measurable)

- [x] Two local processes (this peer + the real opponent, `thief_peer`) complete a real
      HTTP round-trip — `integration_lab/run_negotiation_smoke.py`, evidence in
      `integration_lab/evidence/negotiation_smoke/` (real stdout/stderr/exit codes,
      both sides report `outcome: "negotiated"`).
- [x] Duplicate-message handling behaves per the idempotency policy in the protocol
      contract — same correlation_id + same payload = idempotent accept, same
      correlation_id + different payload = `CONFLICTING_DUPLICATE`, both proven over
      real HTTP in `tests/integration/test_mcp_negotiation.py`.
- [x] Health-check endpoint responds before negotiation — `mcp_client.wait_for_health`,
      bounded retries, tested including the unavailable-peer case (clean timeout, no
      hang).

Only `health`/`negotiate`/`propose_config` are implemented this batch — `receive_turn`/
`submit_audit`/`receive_control` remain schema-only (see `docs/PROTOCOL.md`).

## Out of scope (for now)

Public tunnel exposure (Manual Gate A). Real opponent negotiation with another team
(Manual Gate B) — this batch's "real opponent" is our own `thief_peer` repo, run as a
genuinely separate process, not a stub. Full turn-by-turn game loop (later batch).

Status: minimal vertical slice implemented and tested (Batch 1); full game loop not
started. See `integration_lab/audit/PROGRESS.md`.

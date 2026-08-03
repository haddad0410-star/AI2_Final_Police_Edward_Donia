# PRD fastmcp peer

## Purpose

Define this peer's FastMCP server+client responsibilities.

## Requirements

- Real HTTP transport (`transport="http"`), never an in-process mock in production code.
- Tool surface: `negotiate`, `receive_turn`, `submit_audit`, `receive_control` (see `_post4b_supplementary_evidence/audit/protocol_contract.md`).
- This peer is simultaneously server and client (book Ch.2, Fig.2 symmetric architecture, visually confirmed).
- No central referee; no shared state with the opponent process.

## Acceptance criteria (measurable)

- [x] Two local processes (this peer + the real opponent, `thief_peer`) complete a real
      HTTP round-trip (real stdout/stderr/exit codes, both sides report
      `outcome: "negotiated"`; raw negotiation-smoke evidence was produced during
      development and is not included in this single-repo package).
- [x] Duplicate-message handling behaves per the idempotency policy in the protocol
      contract — same correlation_id + same payload = idempotent accept, same
      correlation_id + different payload = `CONFLICTING_DUPLICATE`, both proven over
      real HTTP in `tests/integration/test_mcp_negotiation.py`.
- [x] Health-check endpoint responds before negotiation — `mcp_client.wait_for_health`,
      bounded retries, tested including the unavailable-peer case (clean timeout, no
      hang).
- [x] Full turn-by-turn game loop (`receive_turn`/`submit_audit`/`receive_control`) is
      implemented and exercised over real HTTP, including a real bilateral
      result-agreement (both peers independently verify matching totals) — see
      `_post4b_supplementary_evidence/batch4b/bilateral_series/`.

`health`/`negotiate`/`propose_config` were the only tools implemented in the original
Batch 1 vertical slice; `receive_turn`/`submit_audit`/`receive_control` have since been
implemented with full lifecycle wiring (see `docs/PROTOCOL.md`).

## Out of scope (for now)

Public tunnel exposure (Manual Gate A). Real opponent negotiation with another team
(Manual Gate B) — local development so far has used our own `thief_peer` repo, run as a
genuinely separate process, not a stub, as the real opponent.

Status: full turn-by-turn game loop implemented and tested, `LOCAL_READY`. Not
`NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY`. See
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

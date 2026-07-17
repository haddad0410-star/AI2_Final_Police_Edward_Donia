# PRD fastmcp peer

## Purpose

Define this peer's FastMCP server+client responsibilities.

## Requirements

- Real HTTP transport (`transport="http"`), never an in-process mock in production code.
- Tool surface: `negotiate`, `receive_turn`, `submit_audit`, `receive_control` (see `integration_lab/audit/protocol_contract.md`).
- This peer is simultaneously server and client (book Ch.2, Fig.2 symmetric architecture, visually confirmed).
- No central referee; no shared state with the opponent process.

## Acceptance criteria (measurable)

- [ ] Two local processes (this peer + a stub opponent) complete a real HTTP round-trip.
- [ ] Duplicate-message handling behaves per the idempotency policy in the protocol contract.
- [ ] Health-check endpoint responds before negotiation.

## Out of scope (for now)

Public tunnel exposure (Manual Gate A). Real opponent negotiation (Manual Gate B).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

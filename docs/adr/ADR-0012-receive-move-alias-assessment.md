# ADR-0012: `receive_move` Alias Assessment

## Status

Accepted (assessment only — not implemented this batch, since `receive_turn` itself
is not implemented yet either; see `docs/PROTOCOL.md`).

## Context

The book's own illustrative FastMCP example (Ch.2.3.2, printed p.28, visually
confirmed) exposes a single tool literally named `receive_move`. The reference-repo
convention we adopted for interoperability (`integration_lab/audit/protocol_contract.md`)
instead uses `receive_turn` as the general-purpose "deliver one turn's sealed record"
tool. An opponent group that implemented the book's example literally, rather than
studying the fuller reference convention, might call a tool named `receive_move`
instead of `receive_turn`.

## Assessment

Can `receive_move` safely forward to `receive_turn` as a pure alias, with zero
duplicated business logic?

**Yes, with one condition.** `receive_turn`'s payload shape (a `TurnRevealMessage` or
similar envelope-wrapped message, see `protocol/messages_turn.py`) is a strict
superset of what the book's minimal `receive_move` example shows (`signed_move: str,
signature: str` — just a move plus a signature, no hint/barrier/envelope metadata).
An alias is safe **only if** it does not attempt to reinterpret or partially fill in
a `TurnRevealMessage` from the narrower `receive_move` shape — that would require
guessing values for fields the caller never sent (e.g., `hint_intent`), which is
exactly the "duplicate/ambiguous business logic" this batch was told to avoid.

## Decision

If/when an alias is implemented (a later batch, once `receive_turn` itself exists):

- `receive_move` MUST be a thin adapter that either (a) rejects any caller that omits
  fields `receive_turn` requires, with a clear `ProtocolErrorMessage`, or (b) is only
  offered for a narrower legacy handshake explicitly negotiated with an opponent who
  is known to only implement the book's minimal example — never a silent default.
- No separate validation, state machine, or commit-reveal logic will ever be written
  for `receive_move`; it only ever calls into `receive_turn`'s implementation.
- This batch does not implement either tool's actual handler (see Stop Condition —
  full game loop is a later batch); this ADR exists so the decision is made
  deliberately once that time comes, rather than improvised.

## Consequences

- Keeps a single source of truth for turn-handling logic.
- Defers a real compatibility decision until we know whether any real opponent
  actually needs the narrower `receive_move` shape (Manual Gate B).

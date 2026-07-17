# PRD commit reveal

## Purpose

Define the cryptographic sealing and mutual audit protocol.

## Requirements

- `H_commit = SHA256(canonical_json({state, move, intent, nonce}))`, fresh CSPRNG nonce per step, hidden until final reveal (Ch.5.3, visually confirmed Fig.6 sequence: Commit -> Acknowledge -> Reveal -> Audit).
- Constant-time comparison on verify (`secrets.compare_digest`).
- Step-0 hardware declaration, sealed before the first move.
- Any recomputation mismatch = `tamper_forfeit`, no partial credit.

## Acceptance criteria (measurable)

- [ ] Security tests deliberately alter move/hint/verdict/nonce/step/config/capture-answer/record-order — every alteration is detected.
- [ ] No nonce is ever reused across steps.
- [ ] Constant-time comparison verified (no early-exit branching on mismatch position).

## Out of scope (for now)

GUI/replay display of audit results (see PRD_gui_replay.md).

Status: design only, not implemented. See `integration_lab/audit/PROGRESS.md`.

# PRD commit reveal

## Purpose

Define the cryptographic sealing and mutual audit protocol.

## Requirements

- `H_commit = SHA256(canonical_json({state, move, intent, nonce}))`, fresh CSPRNG nonce per step, hidden until final reveal (Ch.5.3, visually confirmed Fig.6 sequence: Commit -> Acknowledge -> Reveal -> Audit).
- Constant-time comparison on verify (`secrets.compare_digest`).
- Step-0 hardware declaration, sealed before the first move.
- Any recomputation mismatch = `tamper_forfeit`, no partial credit.

## Acceptance criteria (measurable)

- [x] Security tests deliberately alter move/hint/verdict/nonce/step/config/capture-answer/record-order — every alteration is detected (`tests/security/test_commit_reveal.py`, `tests/security/test_replay_verifier.py`).
- [x] No nonce is ever reused across steps — `tests/security/test_commit_reveal.py::test_fresh_nonce_per_record`, `::test_nonce_reuse_detected_by_audit`.
- [x] Constant-time comparison verified (no early-exit branching on mismatch position) — `tests/security/test_commit_reveal.py::test_constant_time_compare_is_actually_used`.

## Out of scope (for now)

GUI/replay display of audit results (see PRD_gui_replay.md).

Status: implemented and tested. Commit-reveal sealing is unified under the
`commitment/1` schema (`domain/crypto/payload.py`) and used in real gameplay,
including full bilateral (cross-repo) verification. See
`_post4b_supplementary_evidence/audit/PROGRESS.md`.

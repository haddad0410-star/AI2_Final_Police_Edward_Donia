# ADR-0011: "Trapped Thief" Interpretation

## Status

Accepted.

## Context

The implementation batch instructions asked us to implement "Thief having no legal
movement, if the book defines this as trapped" as a possible early-end condition,
alongside ordinary same-cell capture and barrier-placed-on-thief's-cell (Appendix E
rule 46, visually confirmed against Ch.3.4's "Barrier Law" box, printed p.21).

We re-checked `_post4b_supplementary_evidence/audit/visual_verification.md` and
`_post4b_supplementary_evidence/audit/requirements_matrix.md` for an explicit "trapped = automatic
technical loss/capture" rule. We did not find one. What we *did* visually confirm:

- Movement set is constant: N/S/E/W/STAY (Appendix F Table 15, p.137) — **STAY is
  always a legal action**, never conditioned on barriers or board edges.
- Appendix E rule 46: a barrier placed on the cell the thief currently occupies is
  itself a capture.
- Appendix E rule 47: the thief loses if it claims a legal move that is actually
  illegal (a truthfulness rule about move claims, not about being surrounded).

## Decision

Because STAY is unconditionally legal, a thief can never reach a state with *zero*
legal actions under this rule set — "fully trapped" in the literal sense (no legal
action of any kind) is impossible by construction. We therefore do **not** implement
a separate technical-loss/capture rule for "all four orthogonal directions blocked."

`legal_move_directions()` always returns at least `(Direction.STAY,)`, verified by
`tests/unit/test_rules.py::test_stay_is_always_legal_even_when_fully_surrounded`. The
only two conditions that end a sub-game early are the two book-confirmed ones:
`is_ordinary_capture()` and `is_barrier_on_thief_capture()`.

## Consequences

- If a later, more thorough read of the book (or an opponent's differing
  interpretation during negotiation) reveals an explicit "surrounded = auto-loss"
  rule we missed, this ADR and the corresponding rules must be revisited before any
  real league match — flagged in `_post4b_supplementary_evidence/audit/risk_register.md`.
- Strategy code (a later batch) may still choose to treat "all directions blocked,
  only STAY available" as a strong tactical warning signal for the thief, even though
  it is not an automatic rules-level loss.

# Belief Model

Implemented in `src/police_peer/domain/{belief_model,belief_updates}.py`, tested in
`tests/unit/test_belief.py` (13 tests, all passing).

## What this is (and isn't)

This is a **normalized probabilistic belief update** over the opponent's likely
position. It is explicitly **not** claimed to be a formally Bayesian-optimal filter —
the transition/likelihood steps are simple, defensible, testable heuristics (diffusion
transition, multiplicative likelihood, renormalization), described here as
"Bayesian-inspired" at most. No superiority or optimality claim is made.

## Structural guarantee: no true-position leak

No function in `belief_updates.py` accepts the opponent's true position as an
argument — this is enforced by a signature-introspection test
(`test_no_function_accepts_an_opponent_true_position_parameter`), not just a
convention. Every update draws only from: the current belief, a legal-transition
function, a `ScentField` (public evidence), or a hint region (parsed natural-language
evidence).

## Pipeline (frozen, actually wired into the peer runtime as of Batch 3.5 Task 6)

Implemented in `services/belief_update.py::advance_belief`, called once per
turn at the top of `services/turn_loop.py::_decide_turn`, before the
strategy brain is invoked. This section supersedes the pre-Batch-3.5
description of this file (which described a hypothetical future order,
written before the wire pipeline that actually delivers scent/hint evidence
existed at all — see
`integration_lab/evidence/batch3_5/observation_pipeline_audit.md`).

1. **Prior** — `state.belief`, carried over from the previous turn (a fresh
   `uniform_prior(grid_size, barriers)` at sub-game start).
2. **Transition** — `apply_transition(belief, neighbors_fn)`: predict step;
   spreads each cell's mass uniformly over its legal successor cells,
   *before* new evidence is folded in.
3. **Barrier mask** — `apply_barrier_mask(belief, barriers)`: zeroes any
   barrier cell and renormalizes. Applied **before** evidence (not after),
   so a barriered cell can never be re-inflated by a later scent/hint boost
   — both likelihood steps only ever *multiply* existing mass (`0 * x ==
   0`), so masking order matters and is fixed here.
4. **Scent evidence** — `apply_scent_likelihood(belief, scent, trust)`,
   applied **only if** `state.received_scent_valid` is `True`. A malformed
   or missing scent grid takes an explicit missing-evidence path (the step
   is skipped entirely) rather than being silently treated as a genuine
   "nothing nearby" all-zero reading (Batch 3.5 Task 4).
5. **Hint evidence** — `apply_hint_likelihood(belief, hint_region,
   base_trust)`, applied **only if** `state.hint_region is not None` (the
   receiver's best-effort decode of the opponent's hint text — Batch 3.5
   Task 5). The *effective* trust is calibrated by how much the region
   already agrees with existing evidence (`agreement = prior_region_mass *
   grid_size² / |region|`), further scaled by `state.hint_trust` — a
   bounded `[0.05, 0.95]` score updated turn-to-turn by comparing entropy
   before/after the hint is applied (entropy drop -> trust rises; entropy
   rise -> trust falls), **never** derived from the sealed `intent` field
   (which stays hidden from the receiver until the final audit, per the
   "truth/lie intent sealed" absolute rule). A hint can never revive a
   hard-zeroed, physically-impossible cell — verified by
   `tests/unit/test_belief_order.py::test_barrier_mask_applied_before_scent_and_hint`.
6. **Normalization** — every step above renormalizes; a degenerate
   (all-zero) raw grid falls back to a fresh uniform distribution.

## Evidence timing (why it lags by one turn)

Because both peers commit and reveal their own turn *before* receiving the
opponent's same-step reveal (protocol_contract.md §3.3a), evidence for turn
N (the opponent's scent/hint sent that turn) is folded into belief by
`advance_belief` at the **start of turn N+1**, not turn N itself.
`ingest_opponent_reveal` only ever writes into `RuntimeState` fields
(`received_scent`, `received_scent_valid`, `hint_region`) that the *next*
call to `advance_belief` reads exactly once — so step-N evidence is never
applied to step N-1 or step N+1's prediction.

## Duplicate / stale evidence and sub-game reset

Duplicate reveal messages are deduplicated by
`infrastructure/turn_validation.py::TurnRouter` (keyed on
`(sub_game_number, step, sender, message_type)`) before they reach the
inbox a second time; stale (`sequence_id` regression) messages are rejected
with `STALE_SEQUENCE` and never enqueued. Sequence tracking is scoped per
`(sub_game_number, sender)` so a fresh sub-game's sequence restarting at 0
is never confused with a prior sub-game's numbering (risk #16). Every
sub-game starts with a fresh uniform belief, `hint_trust=0.5`, and
`hint_region=None` — nothing carries over from a prior sub-game
(`tests/unit/test_belief_order.py::test_subgame_reset_starts_uniform`).

## Helpers

- `entropy(belief)` — Shannon entropy in bits (0 = certain, `log2(N²)` = maximal
  uncertainty on an N×N board). Verified at both extremes by test.
- `most_likely(belief)` / `top_k(belief, k)` — argmax / ranked list of likely cells.
- `expected_distance(belief, from_position, distance_fn)` — E[distance] under the
  belief, for strategy use in a later batch.

## Degenerate input handling

`normalize()` falls back to a uniform distribution over the whole board if total mass
is ~0 (e.g. all evidence cancels out or barrier-masking zeroes everything) — verified
by `test_degenerate_all_zero_evidence_falls_back_to_uniform`. This never raises and
never returns an invalid (non-normalized) distribution.

## Evidence

`integration_lab/evidence/belief_reference_run.json` — real computed output from this
implementation (uniform prior, transition, scent update, hint update, entropy values),
not fabricated.

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

## Pipeline (per turn, once wired into the peer runtime in a later batch)

1. **Prior** — `uniform_prior(grid_size, barriers)`: uniform over non-barrier cells.
2. **Transition** — `apply_transition(belief, neighbors_fn)`: predict step; spreads
   each cell's mass uniformly over its legal successor cells, *before* new evidence
   is folded in (per the requirement that transition precedes evidence at the
   correct step).
3. **Scent evidence** — `apply_scent_likelihood(belief, scent, trust)`: multiplies
   each cell's probability by `1 + trust * scent_intensity`, then renormalizes.
   All-zero scent evidence is a safe no-op (verified by test).
4. **Hint evidence** — `apply_hint_likelihood(belief, hint_region, base_trust)`:
   boosts the hinted region, but the *effective* trust is calibrated by how much the
   region already agrees with existing evidence (`agreement = prior_region_mass *
   grid_size² / |region|`). A hint that contradicts strong existing evidence gets a
   much smaller boost than one that agrees — verified by
   `test_contradictory_hint_is_down_weighted_not_corrupting`. A hint can never revive
   a hard-zeroed, physically-impossible cell (barrier-masked cells stay exactly 0).
5. **Barrier mask** — `apply_barrier_mask(belief, barriers)`: any newly-revealed
   barrier zeroes its cell and renormalizes the rest.

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

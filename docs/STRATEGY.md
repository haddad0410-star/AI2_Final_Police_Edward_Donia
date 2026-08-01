# Strategy — Police Peer (role-local summary)

**Canonical source:** `_post4b_supplementary_evidence/audit/strategy_proposals.md` — read that first
for the full design, invariants, complexity limits, and evaluation metrics.

This role ships two brains, both implemented (Implementation Batch 3):

1. **`BaselinePoliceBrain`** — a simple, original, from-scratch greedy baseline.
   Not a copy of the reference repository's shipped heuristic. Frozen (Batch 3
   Task 2, regression-tested) as the comparison point for the strategy below.
2. **`BeliefCutoffPoliceBrain`** (`strategy/belief_cutoff_police_brain.py`) — original
   advanced strategy. Batch 3 found no demonstrated capture-rate improvement,
   root-caused to a real observation-pipeline defect (full analysis
   produced during development in the full project workspace; not
   included in this single-repo package) — since
   repaired in **Implementation Batch 3.5** (root-cause write-up likewise
   produced during development, not included in this single-repo
   package). Held-out and
   real-HTTP re-evaluation now shows **100% capture rate for both baseline and
   advanced Police** (a new ceiling tie — still no demonstrated capture-RATE
   improvement), but a real, distinct, previously-nonexistent capability: the
   barrier-placement mechanism now genuinely fires (0 barriers/game for
   baseline, 5-6/game for advanced) and directly causes 70% of captures
   against a baseline Thief. Batch 3.5 also fixed a real bug in the barrier
   gate itself: `barrier_utility_floor` was reused for two purposes with
   opposite sensitivities (the confidence-gate threshold and `_best_barrier`'s
   own minimum-utility floor), making the gate mathematically unreachable
   given the real ~0.30 belief-confidence ceiling under continuous evidence;
   now split into independent `barrier_confidence_gate` (default 0.20) and
   `barrier_utility_floor` (default 0.40) fields. Full root-cause and
   acceptance-criteria analysis was produced during development in the
   full project workspace and is not included in this single-repo
   package. Reported honestly, not hidden. This is a genuinely more sophisticated,
   tested implementation, but no capture-rate superiority claim is made.
   **Implementation Batch 3.6** ran a dedicated fairness/correctness audit
   on top of this result: an 800-game multi-scale robustness check (7x7
   alt-start, 9x9, 11x11, all `RESEARCH_ONLY`) confirmed the 100%-capture
   ceiling persists at every board scale tested — a genuine game-design
   property, not a 7x7-specific artifact — and 6 deterministic behavioral
   fixtures (no true-opponent-position access) proved
   `BeliefCutoffPoliceBrain` and `BaselinePoliceBrain` genuinely choose
   different actions from identical inputs. Final classification: **C**
   (genuine ceiling) **with D** (real behavioral differences) **as a
   corollary** (full write-up produced during development in the full
   project workspace; not included in this single-repo package).

### `BeliefCutoffPoliceBrain` design

Uses the COMPLETE belief distribution (`domain/belief_model.py`'s `top_k`/
`expected_distance`/`entropy`), not just its single most-likely cell:

- **Belief-state pursuit**: scores each legal move by the reduction in
  expected Manhattan distance to the opponent under the full belief mass,
  plus a bonus for landing in a top-3 believed-likely cell.
- **Bounded lookahead** (`belief_cutoff_utility.py::project_belief`, depth 2
  by default): propagates belief forward via the same `apply_transition`
  primitive the real belief pipeline uses, and additionally scores moves by
  the projected post-lookahead expected distance.
- **Entropy-gated exploration**: when belief entropy exceeds a configurable
  threshold (scaled by a hint-trust score), the frontier-exploration term
  activates, preferring low-probability/unvisited cells over direct pursuit.
- **Barrier engineering** (`belief_cutoff_utility.py::barrier_utility`):
  evaluates every legal barrier cell (own cell + orthogonal neighbors) via a
  real BFS reachable-area-reduction measure and proximity to the believed
  region, weighed against remaining quota scarcity — gated by a
  belief-confidence threshold so barriers are not placed on an
  uninformative near-uniform belief.
- **Hint-trust proxy** (`belief_cutoff_hint_trust.py`): the real wire
  protocol folds the opponent's hint into the belief update BEFORE a brain
  ever sees anything — `DecisionRequest` carries only the resulting
  `belief`, never raw hint text. This tracker uses the real, observable
  proxy available to strategy code instead: whether each turn's belief
  update reduced entropy (informative) or increased it (contradictory),
  bounded to `[0, 1]`, feeding the exploration/barrier gates.
- **Utility weights** are a documented, private dataclass
  (`belief_cutoff_config.py::BeliefCutoffWeights`) — never hardcoded inline,
  never part of the signed shared `game.json`. Selected via each peer's own
  `game.toml` `[strategy]` table (`profile`/`weights`).
- **Safety**: inherits `PoliceBrainBase.decide()`'s existing fallback
  (first legal direction, else STAY, on any internal error or an illegal
  proposed move) — always returns a legal action before the deadline.

## Seam

Both subclass a shared `BrainBase` and override `_pick_move` (and optionally
`_decide_move`), invoked strictly between hint-parsing and commit-sealing — the move
is always pure Python; an LLM, if enabled at all, only writes banter text.

## Default banter provider

`template` (0 tokens, no network, no paid API). Any paid provider
(`claude_api`/`claude_cli`/`ollama`) is opt-in only, disabled by default in
`config/police/game.toml`.

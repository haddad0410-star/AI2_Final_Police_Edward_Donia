# Strategy — Police Peer (role-local summary)

**Canonical source:** `integration_lab/audit/strategy_proposals.md` — read that first
for the full design, invariants, complexity limits, and evaluation metrics.

This role ships two brains, both implemented (Implementation Batch 3):

1. **`BaselinePoliceBrain`** — a simple, original, from-scratch greedy baseline.
   Not a copy of the reference repository's shipped heuristic. Frozen (Batch 3
   Task 2, regression-tested) as the comparison point for the strategy below.
2. **`BeliefCutoffPoliceBrain`** (`strategy/belief_cutoff_police_brain.py`) — original
   advanced strategy. **Held-out and real-HTTP evaluation found no demonstrated
   capture-rate improvement over the baseline** in the current experimental
   configuration — see `integration_lab/evidence/batch3/strategy_research/limitations.md`
   for the root-cause analysis (the real wire protocol does not yet deliver
   scent/hint signal to either brain's belief update, so capture within the
   35-move budget is not reliably achievable by either strategy). Reported
   honestly, not hidden. This is a genuinely more sophisticated, tested
   implementation, but no superiority claim is made.

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

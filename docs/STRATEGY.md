# Strategy — Police Peer (role-local summary)

**Canonical source:** `integration_lab/audit/strategy_proposals.md` — read that first
for the full design, invariants, complexity limits, and evaluation metrics.

This role ships two brains, neither implemented yet:

1. **`BaselinePoliceBrain`** — a simple, original, from-scratch greedy baseline.
   Not a copy of the reference repository's shipped heuristic. Exists purely so
   `BeliefCutoffPoliceBrain` has something honest to be measured against.
2. **`BeliefCutoffPoliceBrain`** — our candidate original strategy (see the canonical
   doc for the full design sketch). **No claim of superiority over the baseline is
   made until Phase 7 experiments produce raw data proving it.**

## Seam

Both subclass a shared `BrainBase` and override `_pick_move` (and optionally
`_decide_move`), invoked strictly between hint-parsing and commit-sealing — the move
is always pure Python; an LLM, if enabled at all, only writes banter text.

## Default banter provider

`template` (0 tokens, no network, no paid API). Any paid provider
(`claude_api`/`claude_cli`/`ollama`) is opt-in only, disabled by default in
`config/police/game.toml`.

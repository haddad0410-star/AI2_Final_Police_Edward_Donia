# CLAUDE.md — Police Peer

Project-level rules for this repository. These override generic defaults.

## Architecture rules

- This repo is one independent FastMCP peer (the Police). It must never:
  import from the sibling `thief_peer` repository, import from
  `integration_lab/`, share a config/log/state file path with the opponent, or hold a
  shared in-memory game-state singleton with the opponent.
- All cross-peer communication happens over FastMCP HTTP, using the wire contract in
  `docs/PROTOCOL.md` (canonical source: `integration_lab/audit/protocol_contract.md`).
- Business logic lives in `src/police_peer/domain` and `.../strategy`; the CLI and
  GUI layers call into the SDK (`src/police_peer/sdk`) only — no business logic in
  CLI/GUI code.
- The move is always chosen by pure Python. An LLM may only produce optional banter
  text, never the move itself, unless a signed mutual rule with the opponent says
  otherwise (not expected).

## Exact test commands

```
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=85
uv run python scripts/security_scan.py          # not yet implemented
uv run python scripts/check_file_lengths.py
```

## No-secrets policy

Never commit: `.env`, `credentials.json`, `token.json`, `client_secret*.json`, API keys,
tunnel tokens, or any Gmail OAuth secret. `credentials.json`/`token.json` live **outside**
this repository entirely (path supplied via an environment variable — see
`.env-example`), not merely gitignored inside it.

## 150-line limit

Every submitted Python file must stay at or under 150 meaningful lines (blank lines and
comments excluded). Split modules rather than claiming compliance falsely.

## Protocol compatibility rule

Any change to tool names, message fields, or the four JSON artifact schemas must be
cross-checked against `integration_lab/audit/protocol_contract.md` and, once an
opponent group is known, negotiated with them before a real match. Do not invent
incompatible wire fields for convenience.

## No fabricated evidence rule

Never claim FastMCP execution, test results, coverage, league games, opponent
messages, Gmail delivery, screenshots, or benchmarks that were not actually produced
by running the real thing. Readiness level must never be reported higher than the
evidence in `integration_lab/audit/PROGRESS.md` supports.

## Strategy originality requirement

`BeliefCutoffPoliceBrain` must be a genuinely original design, substantially different
from the reference repository's shipped heuristic. `BaselinePoliceBrain` is our own
simple from-scratch baseline for fair comparison — not a copy of the reference
implementation either. See `integration_lab/audit/reference_reuse_plan.md`.

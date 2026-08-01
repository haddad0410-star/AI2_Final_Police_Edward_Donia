# Limitations — Police Peer

Current, honest state (implementation complete through Batch 4B; readiness:
`LOCAL_READY`):

- A full FastMCP server/client peer is implemented and has repeatedly run
  over real two-process HTTP against the Thief peer.
- Game engine, state machine, both strategies (baseline and advanced),
  scent/belief model, commit-reveal cryptography, a live GUI, a graphical
  replay viewer, and a Gmail dry-run reporter are all implemented and
  tested — see the batch-by-batch history below for what was verified at
  each step.
- `pheromone_min_center_intensity=0.5` (seen in the reference repo's config) is not
  confirmed as a binding Appendix F value — tracked as an open item, not assumed.
  See `_post4b_supplementary_evidence/audit/risk_register.md` risk #2.
- Repository visibility (public vs. private) and its licensing implications are
  unresolved pending your decision — see
  `_post4b_supplementary_evidence/audit/manual_gates.md` Gate E.
- No league opponent, public network exposure, or real Gmail send has
  occurred — these remain open manual gates (A, B, C), not implementation
  gaps.

This file is kept current every batch — never allowed to go stale while claiming
a higher readiness level than `_post4b_supplementary_evidence/audit/PROGRESS.md` supports.

## Current state (Implementation Batch 4A)

- **Live GUI, replay viewer, Gmail dry-run reporting, and public-network
  preparation are now implemented and tested** — league play, real Gmail
  send, and public network exposure are still not done (see below).
- The graphical replay viewer surfaced a genuine, previously-unknown
  cross-schema incompatibility: this repo's own replay-verification
  engine cannot correctly recompute the opponent's differently-shaped
  commitment hashes (`sealed-turn/2` vs this repo's `commit-reveal/2`).
  Fixed by never claiming a verdict this repo's crypto module cannot
  actually compute — the opponent's side is loaded for display only,
  honestly labeled `NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE`. **RESOLVED
  in Batch 4B** — see below; this was a real, mechanical schema
  divergence, fixable without cross-repo imports, not a fundamental limit.
  A genuinely cross-repo LEGACY (pre-Batch-4B) record is still subject to
  this limitation; see the Batch 4B section below for the precise scope.
- The live GUI's "runtime latency" and "decision latency" figures are
  real measured values from this process, not simulated; the live GUI's
  "connection status" is derived from protocol-level exchange success/
  failure (reveal received or not), not a raw socket-level connection
  event — this repo does not currently instrument socket-level connect/
  disconnect events separately.
- Gmail `--send` mode exists in real, tested code (routed through a real
  Gatekeeper) but has never been invoked; it requires the
  `gmail-send` optional dependency group to be installed explicitly
  (`uv sync --extra gmail-send`) and real OAuth credentials outside this
  repo, neither of which exist in this environment.
- Public-network preparation (`infrastructure/public_auth.py`) is
  real, tested code, but the server's existing hard localhost-only bind
  guard is deliberately unchanged — going public would require a
  separate, reviewed code change plus your explicit approval, not just
  an environment variable.
- Readiness: `LOCAL_READY` (unchanged — Batch 4A adds local
  tooling/UI/reporting on top of an already-`LOCAL_READY` baseline;
  `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY` still not claimed).

## Current state (Implementation Batch 4B)

- **Bilateral commitment verification is now real, not display-only.**
  Both repos' sealed field set is unified under a versioned
  `commitment/1` schema (`domain/crypto/payload.py`); this repo's own
  crypto module now correctly recomputes and verifies a genuine Thief
  `commitment/1` record, and vice versa. `NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE`
  is now `NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE_LEGACY_SCHEMA` and only
  applies to genuinely pre-Batch-4B legacy records (Batch 1-4A evidence,
  preserved unmodified on disk and still self-verifiable under its own
  original schema) — never to a current `commitment/1` record. Full
  evidence: `_post4b_supplementary_evidence/batch4b/` (schema audit, 10
  byte-identical cross-repo test vectors, a 21-category bilateral tamper
  matrix, a real six-sub-game two-process series with
  `FULL_BILATERAL_VERIFICATION=true` both sides, and a bilaterally-gated
  Gmail dry-run reporter).
- Readiness: `LOCAL_READY` (unchanged — bilateral verification is a local
  correctness property; `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY`
  still not claimed. No public binding, OAuth, real Gmail send, GitHub
  repo, or real opponent contact occurred in Batch 4B).

## Current state (Implementation Batch 3.6)

- A dedicated epistemic-fairness, scent-timing, capture-correctness, and
  strategy-distinguishability audit was run on top of Batch 3.5's repair,
  triggered by Batch 3.5's own headline result (100% Police capture / 0%
  Thief survival in every matchup) being a **new ceiling tie in the
  opposite direction** — technically successful, scientifically
  inconclusive about strategy quality on its own.
- **No exact-position leakage found**: a real 200-random-walk quantitative
  simulation over production `domain.scent`/`domain.belief_updates` code
  shows scent produces a uniquely-peaked candidate reading on 100% of
  turns, but that peak matches the true opponent position only **30.5%**
  of the time, and belief entropy barely drops (5.61 -> 5.36 bits) — a
  confident-looking maximum-likelihood signal, not a leak of the true
  cell. (Full simulation write-up produced during development in the full
  project workspace; not included in this single-repo package.)
- **No hint-verdict early-visibility defect found**: the intent
  (truth/lie) verdict is confirmed absent from the live `reveal` payload
  and present/verifiable only at final audit, both by direct code
  inspection and 3 new end-to-end tests.
- **800-game multi-scale robustness check** (7x7 alt-start, 9x9, 11x11;
  RESEARCH_ONLY, never replacing the binding 7x7 league config) confirms
  the 100%-capture ceiling is a genuine **game-design property of this
  board/geometry and greedy pursuit/evasion dynamics**, not a
  7x7-specific implementation artifact — mean steps scale proportionally
  with board size (12 -> 16 -> 20).
- Real behavioral differences between baseline and advanced strategies
  **do exist** even though they don't move the capture-rate ceiling: 6
  deterministic action-divergence fixtures (no true-opponent-position
  access), advanced Police's higher belief-entropy reduction (3.27 vs
  2.48 bits) and barrier usage (6/game vs 0/game) on this batch's paired
  seeds.
- One process error was self-caught and disclosed: the existing (Batch
  3.5-scoped) capture-sanity script regenerated Batch 3.5's evidence
  files in place before being replaced with a properly-scoped Batch 3.6
  version; content was verified materially identical. One real HTTP
  series showed a transient sub-game failure (system-load-dependent,
  reproduced 0 times on a clean rerun); both are disclosed in evidence
  produced during development in the full project workspace (not included
  in this single-repo package).
- Final classification: **C (genuine game-design ceiling, honestly
  documented) with D (real behavioral differences exist) as a direct
  corollary** — not A/B/E. (Full write-up produced during development in
  the full project workspace; not included in this single-repo package.)
- Full evidence set (scent-timing contract with book page citations,
  leakage audit, hint-visibility audit, causal ablation across 9
  evidence-source conditions, capture-correctness re-audit, 6 behavioral
  fixtures, secondary metrics, 800-game robustness results,
  research/production equivalence, real HTTP series) was produced during
  development in the full project workspace and is not included in this
  single-repo package. The 7 figures are bundled at
  `_post4b_supplementary_evidence/batch3_6_figures/`.
- Readiness: `LOCAL_READY` (unchanged — Batch 3.6 is a fairness/
  correctness audit on top of an already-`LOCAL_READY` baseline;
  `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY` still not claimed).

## Current state (Implementation Batch 3.5)

- The observation-pipeline defect identified in Batch 3 (below) is
  **repaired**: real scent/hint evidence now genuinely reaches belief
  updates over the real wire protocol, and a real, additional
  capture-confirmation defect (`claim_response` had the identical
  dead-message-type bug as the scent grid — found while building capture
  sanity fixtures) is also fixed. Held-out evaluation (400 games) and real
  HTTP validation (18 sub-games, 3 series) now show **100% Police capture
  rate in every matchup** — a complete reversal from Batch 3's 0%.
- This is a **new ceiling tie** (capture, not survival), honestly analyzed
  in a write-up produced during development in the full project workspace
  (not included in this single-repo package):
  `BeliefCutoffPoliceBrain` shows **no demonstrated capture-rate
  improvement** over `BaselinePoliceBrain` (both 100%, ceiling-tied), but
  does show real, repeatable barrier usage (0 barriers/game for baseline,
  5-6/game for advanced) and directly causes 70% of captures via the
  barrier mechanism specifically when facing a baseline Thief — a
  genuinely new, functioning capability, not previously observable at all.
  Barrier threshold logic itself was also fixed (Task 8): a Batch 3 field
  (`barrier_utility_floor`) was reused for two purposes with opposite
  sensitivities, making the confidence gate mathematically unreachable;
  now split into independent `barrier_confidence_gate`/`barrier_utility_floor`
  fields.
- Full analysis (root cause, audit, before/after traces, barrier repair,
  capture sanity fixtures, held-out and real-HTTP results, figures) was
  produced during development in the full project workspace and is not
  included in this single-repo package.
- Readiness: `LOCAL_READY` (unchanged — Batch 3.5 repairs a functional
  defect and re-validates on top of an already-`LOCAL_READY` baseline;
  `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY` still not claimed).

## Current state (Implementation Batch 3)

- `BeliefCutoffPoliceBrain` is implemented, unit-tested (22 tests), and
  validated over 3 real six-sub-game HTTP series — but held-out research
  evaluation (100 games) and the real HTTP series both found **no
  demonstrated capture-rate improvement** over `BaselinePoliceBrain` in the
  current experimental configuration (both 0% captures). Root cause: the
  real wire protocol does not currently deliver scent or hint signal to
  either brain's belief update, so belief never concentrates enough for
  the barrier-confidence gate to open — a pre-existing system
  characteristic, not a defect in this batch's strategy code. Full
  analysis was produced during development in the full project workspace
  and is not included in this single-repo package.
- GUI, Gmail reporting, public network exposure, and league play remain
  not implemented/run, unchanged from session recovery step C.
- `pheromone_min_center_intensity=0.5` remains unconfirmed as binding (risk
  #2, unchanged). Repository visibility/licensing consent (Manual Gate E)
  remains unresolved, unchanged.
- Readiness: `LOCAL_READY` (unchanged from session recovery step C — Batch
  3 adds strategy work on top of an already-`LOCAL_READY` local P2P
  baseline; `NETWORK_READY`/`LEAGUE_READY`/`SUBMISSION_READY` still not
  claimed).

## Current state (session recovery step C)

- Implemented and independently verified: config loading, domain
  models/board physics, scent/belief, protocol schemas, commit-reveal
  crypto, canonical `declaration/2` Step-0 declaration, state machine,
  deadline tracker, watchdog, baseline strategy brain, template hints,
  sub-game runtime, series runtime, JSON artifact generation, and the
  headless replay verifier.
- **New this step**: a real two-process game/series against the actual
  Thief opponent (one sub-game and a full six-sub-game series, both over
  real FastMCP HTTP), and the mutual cross-repo artifact/audit comparison
  (96/96 checks passed) — both previously unimplemented/unrun, now done.
  Six real cross-repo protocol/wiring defects were found and fixed only by
  actually running two independent processes against each other — see
  `CHANGELOG.md` and `risk_register.md` risks #15-#16.
- **Still not implemented or run**: `BeliefCutoffPoliceBrain` (only the
  from-scratch baseline exists), a live GUI, a replay *viewer* (the
  headless verifier exists; a visual viewer does not), Gmail reporting,
  public network exposure/tunnel, and league play.
- The declaration schema divergence between this repo and the Thief repo
  (risk #14) is **resolved** — canonical `declaration/2`, verified
  byte-identical fixtures.
- `pheromone_min_center_intensity=0.5` remains unconfirmed as binding (risk
  #2, unchanged from Batch 1).
- Repository visibility/licensing consent (Manual Gate E) remains
  unresolved, unchanged from Batch 1.
- Readiness: `LOCAL_READY` (session recovery step C). `NETWORK_READY`/
  `LEAGUE_READY`/`SUBMISSION_READY` not claimed.

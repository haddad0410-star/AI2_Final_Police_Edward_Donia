# Screenshots — Police Peer (manual capture instructions)

No screenshot in this repository is fabricated or auto-generated. This
file gives exact commands and manual steps so you (Edward/Donia) can
capture real screenshots yourselves. Claude has already run both peers'
real live GUI end to end (real FastMCP HTTP, real commit-reveal, real
capture/survival outcomes) and confirmed it works (both
replay verifiers report `VERIFIED`; raw summary JSON produced during
development in the full project workspace, not included in this
single-repo package) — but taking the actual screenshots
requires a human at the keyboard.

**Batch 4B update**: the replay viewer now performs FULL BILATERAL
verification (both sides' commitments independently recomputed by each
repo's own crypto module under the unified `commitment/1` schema — see
`_post4b_supplementary_evidence/batch4b/commitment_schema_audit.md`), so the
valid-series banner text changed from a single-sided verdict to
`VERIFIED — BOTH PEERS INDEPENDENTLY VERIFIED`. Captures 6–9 below point
at the new real bilateral evidence
(`_post4b_supplementary_evidence/batch4b/bilateral_series/`), not the Batch 4A
evidence (which remains valid, preserved, legacy-schema evidence — still
viewable, just not what these specific captures reference).

## Prerequisites

Both commands below must run from the repo root, in two separate terminal
windows, started within a few seconds of each other (each peer's own
`response_timeout_sec=30` applies while waiting for the other to connect).

## 1. Police live GUI

```bash
cd police_peer
uv run python -m police_peer peer --gui --config-dir config/police \
  --opponent-url http://127.0.0.1:8902/mcp
```

## 2. Thief live GUI (start within a few seconds, separate terminal)

```bash
cd thief_peer
uv run python -m thief_peer peer --gui --config-dir config/thief \
  --opponent-url http://127.0.0.1:8901/mcp
```

Both windows auto-close ~8 seconds after the game finishes
(`gui/tk_app.py`'s `AUTO_CLOSE_GRACE_MS`) — take your screenshots during
that window, or click "Quit" only after you're done capturing (closing
early on one side ends the other side's sub-game as a technical loss).

## What to capture (9 total)

1. **Police live GUI, early game** — the board showing your own position/
   path, the "LIVE VIEW — OPPONENT TRUE POSITION HIDDEN" banner, and the
   status panel (state machine state, strategy class, connection status).
2. **Belief heatmap** — the second canvas, showing the shaded probability
   grid over where Police believes the Thief might be (gold-outlined cells
   = top-5 most likely).
3. **Barrier placement** — once `BeliefCutoffPoliceBrain` places a barrier
   (visible as a dark cell on the board canvas and in the event log panel
   on the right), capture that moment. **Requires the advanced-strategy
   config, not the Prerequisites command above**: the default
   `config/police` profile loads `BaselinePoliceBrain`, which by design
   never places a barrier (`strategy/baseline_police_brain.py`) — this
   capture is unreachable with the Prerequisites command. Use instead:
   ```bash
   cd police_peer
   uv run python -m police_peer peer --gui --config-dir config/police_advanced \
     --opponent-url http://127.0.0.1:8902/mcp
   ```
   (paired with the Thief side's `config/thief_advanced`, same ports —
   see `thief_peer/screenshots/README.md`). This profile is identical to
   `config/police` except `[strategy].police_class` points at
   `BeliefCutoffPoliceBrain`; same class/profile/seed combination already
   verified to place barriers (`barrier_count=8` in all 6 sub-games, no
   technical loss, both sides' bilateral replay `VERIFIED`) in
   `_post4b_supplementary_evidence/batch4b/bilateral_series/police_config/game.toml`
   and reproduced headlessly for this correction.
4. **Protocol status** — the status panel's `last_message_type`,
   `commit_sent`/`ack_received`/`reveal_sent`/`reveal_received` fields
   (Batch 4B: now real per-substep values read live from the actual
   commit/ack/reveal exchange, never hardcoded — see
   `services/turn_gui_publish.py` and `infrastructure/http_transport.py`).
   In practice each turn only lasts ~100ms, too fast to screenshot mid-turn
   reliably — the easiest reliable capture is right after the game ends:
   the LAST completed turn's values stay frozen on screen for the full ~8s
   auto-close window (nothing resets them at game end), so capture then.
5. **Capture/result banner** — the red banner turning into
   "SUB-GAME OVER: CAPTURE" (or SURVIVAL/TECHNICAL LOSS) at game end. The
   live window auto-closes ~8s after the game finishes
   (`gui/tk_app.py`'s `AUTO_CLOSE_GRACE_MS`) — capture within that window.

Save files 1–5 here as `police_live_<description>.png`. Do not edit, crop
out data, or stage a fake result — if a run ends in something other than
capture, that is the real, honest outcome; save it as such.

## Replay viewer captures (bilateral series, Batch 4B)

```bash
cd police_peer
uv run python -m police_peer replay --gui \
  --police-artifacts _post4b_supplementary_evidence/batch4b/bilateral_series/police_artifacts \
  --thief-artifacts _post4b_supplementary_evidence/batch4b/bilateral_series/thief_artifacts
```

This window stays open until you click a control or close it (no
auto-close) — take your time.

6. **Full bilateral verification banner** — the green
   `VERIFIED — BOTH PEERS INDEPENDENTLY VERIFIED` banner (confirmed real
   headless output: `_post4b_supplementary_evidence/batch4b/bilateral_series/bilateral_checks.json`).
7. **Sub-game selector + a capture step** — the selector row across all 6
   real sub-games, with a capture step selected showing both true paths
   converging.
8. **Barrier visible on the board** — any step where Police placed a
   barrier during the real series (`barrier_count` per sub-game is in
   `_post4b_supplementary_evidence/batch4b/bilateral_series/summary.json`).

### 9. TAMPERED demonstration (real, not staged)

`_post4b_supplementary_evidence/batch4b/bilateral_series/tampered_copy/`
contains a COPY of the real bilateral series with one field
(`steps[0].move` in `police_artifacts`) edited in the copy only — the
original evidence under `bilateral_series/` was never touched (still
verifies `VERIFIED`, confirmed directly, both directions). Reproduce:

```bash
cd police_peer
uv run python -m police_peer replay --gui \
  --police-artifacts _post4b_supplementary_evidence/batch4b/bilateral_series/tampered_copy/police_artifacts \
  --thief-artifacts _post4b_supplementary_evidence/batch4b/bilateral_series/tampered_copy/thief_artifacts
```

Real headless output (confirmed identical via the actual Tkinter
`VerdictBanner` widget, see
`_post4b_supplementary_evidence/batch4b/graphical_replay_regression/README.md`):
```
REPLAY VERDICT: TAMPERED
FULL_BILATERAL_VERIFICATION=false
police: independently_verified=True verdict=TAMPERED
thief: independently_verified=True verdict=VERIFIED
  - sub-game 1: commitment hash mismatch (tamper) (step 0)
```
Capture the red `TAMPERED — TAMPERED` banner with this finding listed.
Never edit or replace the original, valid evidence to produce this —
always work on a fresh copy.

Save files 6–9 here as `police_replay_<description>.png`.

## Reproducibility

Real two-independent-process evidence (no GUI needed to reproduce the
underlying game) is at `_post4b_supplementary_evidence/batch4b/bilateral_series/`
(current, bilateral-schema series: commands, PIDs, stdout/stderr, exit
codes, both sides' replay-verify output, bilateral cross-verification
checks). The preserved legacy-schema evidence from Batch 4A
(`integration_lab/evidence/batch4a/gui_demo/`) was produced during
development in the full project workspace and is not included in this
single-repo package.

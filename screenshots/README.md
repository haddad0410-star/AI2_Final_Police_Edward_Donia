# Screenshots — Police Peer (manual capture instructions)

No screenshot in this repository is fabricated or auto-generated. This
file gives exact commands and manual steps so you (Edward/Donia) can
capture real screenshots yourselves. Claude has already run both peers'
real live GUI end to end (real FastMCP HTTP, real commit-reveal, real
capture/survival outcomes) and confirmed it works — see
`integration_lab/evidence/batch4a/gui_demo/gui_demo_summary.json` (both
replay verifiers report `VERIFIED`) — but taking the actual screenshots
requires a human at the keyboard.

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

## What to capture

1. **Police live GUI, early game** — the board showing your own position/
   path, the "LIVE VIEW — OPPONENT TRUE POSITION HIDDEN" banner, and the
   status panel (state machine state, strategy class, connection status).
2. **Belief heatmap** — the second canvas, showing the shaded probability
   grid over where Police believes the Thief might be (gold-outlined cells
   = top-5 most likely).
3. **Barrier placement** — once `BeliefCutoffPoliceBrain` places a barrier
   (visible as a dark cell on the board canvas and in the event log panel
   on the right), capture that moment.
4. **Protocol status** — the status panel's `last_message_type`,
   `commit_sent`/`ack_received`/`reveal_sent`/`reveal_received` fields
   updating turn to turn (visible if you resize/inspect during play).
5. **Capture/result banner** — the red banner turning into
   "SUB-GAME OVER: CAPTURE" (or SURVIVAL/TECHNICAL LOSS) at game end.

Save files here as `police_live_<description>.png`. Do not edit, crop out
data, or stage a fake result — if a run ends in something other than
capture, that is the real, honest outcome; save it as such.

## Replay viewer captures

```bash
cd police_peer
uv run python -m police_peer replay --gui \
  --police-artifacts ../integration_lab/evidence/batch4a/gui_demo/six_subgame_series/police_artifacts \
  --thief-artifacts ../integration_lab/evidence/batch4a/gui_demo/six_subgame_series/thief_artifacts
```

Capture: (a) the green "VERIFIED" banner, (b) the sub-game selector row,
(c) a capture step showing both true paths converging, (d) a step with a
barrier visible on the board.

### TAMPERED demonstration (already reproduced once, real — not staged)

Claude already ran this for real: `integration_lab/evidence/batch4a/replay_demo/`
contains a COPY of the real six-sub-game evidence with one field
(`steps[0].move`) edited in the copy only — the original evidence under
`integration_lab/evidence/batch4a/gui_demo/` was never touched (still
verifies `VERIFIED`, confirmed directly). Reproduce the screenshot with:

```bash
cd police_peer
uv run python -m police_peer replay --gui \
  --police-artifacts ../integration_lab/evidence/batch4a/replay_demo/police_artifacts_TAMPERED_COPY \
  --thief-artifacts ../integration_lab/evidence/batch4a/replay_demo/thief_artifacts_COPY
```

Real headless output (`integration_lab/evidence/batch4a/replay_demo/tampered_demo_output.txt`):
```
REPLAY VERDICT: TAMPERED
  - sub-game 1: commitment hash mismatch (tamper) (step 0)
```
Capture the red "TAMPERED" banner with this finding listed. Never edit or
replace the original, valid evidence to produce this — always work on a
fresh copy.

## Reproducibility

Exact real-process evidence (no GUI needed to reproduce the underlying
game) is at `integration_lab/evidence/batch4a/gui_demo/` — commands,
stdout/stderr, exit codes, and artifact paths for both a smoke sub-game and
a full six-sub-game series, both run with `--gui` for real.

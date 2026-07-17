# Screenshots

No screenshots exist yet — this project's rules explicitly forbid fabricating PNG
screenshots (see the root CLAUDE.md's "no fabricated evidence" rule and the master
plan's Phase 10). Screenshots are only added here once the live GUI and replay viewer
are actually implemented and actually run.

## Exact manual capture commands (to be run once the GUI exists)

```
# Live GUI, belief-heatmap view (per-peer, own true state only):
uv run python -m <package> peer --role <role>
# then manually capture the window, e.g. on macOS:
#   Cmd+Shift+4, click the game window
# Save as: screenshots/live_belief_heatmap.png

# Replay viewer, showing VERIFIED after a completed local match:
uv run python -m <package> replay --log logs/<group_id>/log_<game_id>_g01.json
# Save as: screenshots/replay_verified.png
```

Do not add any image to this directory that was not produced by actually running the
commands above against real, working code.

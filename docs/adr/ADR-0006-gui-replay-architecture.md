# ADR-0006: Gui Replay Architecture

## Status

Accepted

## Context

The GUI must never leak the opponent's true position live, but the replay viewer must show both tracks after the fact with full hash re-verification (book Ch.7).

## Decision

Headless-compatible GUI module: a pure data/state layer usable without a display for testing, with a Tkinter (or equivalent) rendering layer on top. Live view and replay view share the data layer but not the rendering rules (live hides the opponent, replay reveals after game end).

## Consequences

GUI-model tests can run in CI without a display; only manual screenshots require an actual windowed session (see `screenshots/README.md`).

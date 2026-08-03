# ADR-0010: Python Version

## Status

Accepted

## Context

See `_post4b_supplementary_evidence/audit/adr/ADR-0009-python-version.md` for the full investigation (installed versions, FastMCP's actual `>=3.10` requirement vs. the reference repo's non-binding `>=3.13` preference, uv support).

## Decision

Target Python 3.11 (`.python-version`, `pyproject.toml` `requires-python=">=3.11"`) — already installed locally, satisfies FastMCP's real floor with margin, no new interpreter download needed.

## Consequences

Upgrading later (e.g. to 3.13) is a single approved `uv python install` away if a real dependency need arises.

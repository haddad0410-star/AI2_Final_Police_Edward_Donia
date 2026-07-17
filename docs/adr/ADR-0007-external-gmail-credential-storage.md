# ADR-0007: External Gmail Credential Storage

## Status

Accepted

## Context

Rule 12 forbids ever committing `credentials.json`/`token.json`, and the book's Appendix A requires the same. Gitignoring inside the repo is not sufficient defense-in-depth on its own.

## Decision

Both files must live in a directory entirely outside both repositories, referenced only via an environment variable (`GMAIL_CREDENTIALS_DIR`). `.gitignore` still blocks them as a second layer, not the only layer.

## Consequences

Every developer machine needs local, out-of-repo setup before Gmail reporting can run at all — acceptable since it only affects Manual Gate C, not local/network game-play.

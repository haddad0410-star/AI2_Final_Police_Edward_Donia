# Public Network Setup — Police Peer

**Status: preparation only. No tunnel has been started, no public endpoint
has been tested, and this peer has never bound to anything other than
localhost.** This document and the code it describes exist so that, once
you approve Manual Gate A, going public is a reviewed, deliberate step —
not a rewrite.

## What already exists (implemented, tested, never activated)

- `infrastructure/server_lifecycle.py`'s `ManagedServer` hard-blocks any
  bind host other than `127.0.0.1`/`localhost`/`::1`
  (`_ALLOWED_LOCAL_HOSTS`) — unchanged this batch. Public binding is not
  currently possible even by accident.
- `infrastructure/public_auth.py` (Batch 4A): bearer-token resolution and
  constant-time verification, built and tested (`tests/security/test_public_auth.py`,
  7 tests), but not yet wired into the live server — see "What is NOT done
  yet" below.

## Token handling (when this is eventually wired in)

- Source: `PUBLIC_BIND_TOKEN` environment variable only. Never a
  `game.toml`/`game.json` field — those are (or could be) committed;
  a token must never be.
- `public_auth.resolve_bind_token()` requires the token to be present and
  at least 32 characters; `verify_bearer_token()` uses
  `hmac.compare_digest` (constant-time) — never `==`.
- Never logged, never echoed in an error message, never printed by any
  script in this repo (verified by `tests/security/test_public_auth.py::test_token_never_appears_in_error_message`).

## Revocation

If a `PUBLIC_BIND_TOKEN` is ever suspected leaked:
1. Generate a new one: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Set the new value in the environment used to launch the peer (never in
   a committed file).
3. Restart the peer process.
4. If a tunnel provider issued its own separate access token, revoke that
   in the provider's own dashboard too.

(Also available programmatically: `public_auth.revocation_instructions()`.)

## HTTPS requirement

A raw public HTTP endpoint is never acceptable — public exposure requires
a tunnel or deployment that terminates HTTPS.
`check_public_endpoint.py <url>` (development-workspace script, not included
in this standalone package) validates the URL FORM (scheme, hostname, path)
before you ever go live — it never opens a socket or contacts the URL.

## What is NOT done yet (deliberately, pending your approval)

- `ManagedServer`'s host allowlist has NOT been loosened — going public
  requires a separate, reviewed code change plus your explicit approval,
  not just setting an env var.
- No tunnel (ngrok/Cloudflare Tunnel/etc.) has been started, configured,
  or has an account associated with this project.
- No real bearer token has ever been generated or used.
- No public endpoint has ever been contacted.

## Pre-flight checklist (run before ever requesting Gate A approval)

- [ ] `check_public_endpoint.py <intended-url>` passes (development-workspace
      script, not included in this standalone package).
- [ ] `check_peer_auth.py` passes (development-workspace script, not included
      in this standalone package).
- [ ] `check_port_release.py` shows no orphans (development-workspace script,
      not included in this standalone package).
- [ ] Reviewed which code change would be needed to loosen
      `_ALLOWED_LOCAL_HOSTS` and how the bearer token would be enforced
      on every incoming request.
- [ ] Your explicit written approval for Gate A.

Readiness remains `LOCAL_READY`. This document does not raise readiness by
itself — see `_post4b_supplementary_evidence/audit/PROGRESS.md`.

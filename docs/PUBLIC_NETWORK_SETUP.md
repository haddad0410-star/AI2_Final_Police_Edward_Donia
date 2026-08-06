# Public Network Setup — Police Peer

**Status: Gate A1 (local auth/rate-limit implementation) is done. No tunnel
has been started, no public endpoint has been tested, and this peer has
never bound to anything other than localhost.** `--public` mode is real,
tested, and enforced end to end over real loopback HTTP -- but it is only
ever exercised against `127.0.0.1` in this repo's own tests. Going public
(actually starting a tunnel) is a separate, later, explicit approval
(Gate A2), not a code change.

## What is now implemented, tested, and wired in (Gate A1)

- `infrastructure/server_lifecycle.py`'s `ManagedServer` still hard-blocks
  any bind host other than `127.0.0.1`/`localhost`/`::1`
  (`_ALLOWED_LOCAL_HOSTS`) — **unchanged, never loosened**. `--public` mode
  changes only whether auth/rate-limit middleware is attached; it never
  changes what host is bound.
- `infrastructure/auth_middleware.py`'s `BearerAuthMiddleware`: raw ASGI
  middleware enforcing `Authorization: Bearer <PUBLIC_BIND_TOKEN>` on every
  HTTP request, applied via `FastMCP.http_app(middleware=...)` — before
  FastMCP's own routing/tool dispatch, never inside an individual
  `@mcp.tool`. Constant-time comparison (`hmac.compare_digest`).
- `services/incoming_gatekeeper.py`'s `IncomingGatekeeper` +
  `infrastructure/mcp_rate_limit_middleware.py`'s `McpRateLimitMiddleware`:
  bounds concurrent in-flight LOGICAL operations and the rolling per-minute
  rate, honestly rejecting rather than queuing forever. **Gate A1
  correction:** this is FastMCP protocol-level middleware
  (`FastMCP.add_middleware`, hooking `on_call_tool`), not ASGI-level --
  it charges exactly one accounting event per real tool call
  (`negotiate`/`propose_config`/`receive_turn`/`submit_audit`/
  `receive_control`; `health` excluded as a liveness probe), never the ~6
  raw HTTP requests FastMCP's own session/capability/teardown plumbing
  needs underneath one logical call. Config-driven from `rate_limits.json`'s
  top-level block (30/min, 2 concurrent, queue 100 — the same binding
  minimums), never a hardcoded second copy. Independent of the Gmail
  sender's own `Gatekeeper` — no shared mutable state.
- `infrastructure/outbound_pacer.py`'s `OutboundPacer` (Gate A1 correction):
  proactively paces outbound calls to a `--public` opponent under the same
  binding minimums, so a compliant client rarely if ever needs the
  opponent to reject anything. Waits (never rejects) for a slot; only
  constructed when calling an opponent that requires a token.
- `sdk/public_mode.py`: `resolve_public_tokens()` fails closed if
  `--public` is given without a nonempty `PUBLIC_BIND_TOKEN`;
  `build_public_middleware()` registers the MCP-level rate limiter on the
  server directly and returns the ASGI auth middleware list, so an
  unauthenticated request is rejected before MCP dispatch (and thus the
  rate limiter) ever runs.
- `--public` is a real flag on `run-subgame`/`run-series`/`peer`
  (`__main__.py` / `cli_runners.py`). Without it, local behavior is
  provably unchanged (existing test suite, unmodified, still green).
- Client side: `infrastructure/mcp_client.py` adds
  `Authorization: Bearer <OPPONENT_MCP_TOKEN>` only when a token is given
  (`fastmcp.client.auth.bearer.BearerAuth`, backed by `pydantic.SecretStr`
  so it can never leak via a plain `repr()`); a local/no-token call is
  byte-for-byte the same request it always was. A real overload response
  is retried (honoring the server's `retry_after_seconds`, bounded by the
  binding minimum retry count) rather than failing immediately.

## Token handling

- Sources: `PUBLIC_BIND_TOKEN` (this peer's own, required by `--public`)
  and `OPPONENT_MCP_TOKEN` (the opponent's, only if THEY require one) —
  both environment variables only. Never a `game.toml`/`game.json` field —
  those are (or could be) committed; a token must never be. One
  independently generated token per peer — Police and Thief must never
  share one.
- Generate with `python3 integration_lab/scripts/generate_public_token.py`
  (prints one `secrets.token_urlsafe(32)` value to stdout, nothing else,
  never written to a file).
- Server side: `BearerAuthMiddleware` uses `hmac.compare_digest` — never
  `==`. Client side: `BearerAuth`'s `SecretStr` wrapper. Neither is ever
  logged, echoed in an error message, or printed by any script in this
  repo — proven by `tests/unit/test_auth_middleware.py`,
  `tests/unit/test_mcp_client_token.py`, and
  `integration_lab/scripts/check_local_public_auth.py`'s
  `token_never_disclosed_in_response` check.

## Revocation

If a `PUBLIC_BIND_TOKEN`/`OPPONENT_MCP_TOKEN` is ever suspected leaked:
1. Generate a new one (`generate_public_token.py`, above).
2. Set the new value in the environment used to launch the peer (never in
   a committed file).
3. Restart the peer process — the new token takes effect immediately, the
   old one is rejected immediately.
4. If a tunnel provider issued its own separate access token, revoke that
   in the provider's own dashboard too.

(Also available programmatically: `public_auth.revocation_instructions()`.)

## HTTPS requirement

A raw public HTTP endpoint is never acceptable — public exposure requires
a tunnel or deployment that terminates HTTPS (Cloudflare Tunnel is the
recommended option for this project — see the Gate A read-only preflight
report). `check_public_endpoint.py <url>` (development-workspace script,
not included in this standalone package) validates the URL FORM (scheme,
hostname, path) before you ever go live — it never opens a socket or
contacts the URL. Once a real tunnel URL exists, Cloudflare Tunnel
forwards HTTPS traffic to this peer's `127.0.0.1` port only — this
process itself never terminates TLS and never binds anything but
loopback. A Quick Tunnel is temporary testing/league infrastructure, not
a permanent production deployment.

## What is still NOT done (Gate A2, deliberately, pending your approval)

- No tunnel (Cloudflare Tunnel/ngrok/etc.) has been started, installed, or
  configured.
- No real bearer token has ever been used against anything but
  `127.0.0.1`.
- No public endpoint has ever been contacted — `check_remote_public_auth.py`
  (development-workspace script) refuses to run without an explicit
  `--confirm` flag, specifically so it can never fire by accident.

## Startup and shutdown order (once Gate A2 is approved)

1. `check_port_release.py` — confirm ports free, no orphan process
   (patterns now include `cloudflared`/`ngrok`, not just this repo's own
   processes).
2. `export PUBLIC_BIND_TOKEN=$(generate_public_token.py)` for each peer
   (independently).
3. Start each peer with `--public`.
4. Start each peer's own tunnel process, forwarding to that peer's
   `127.0.0.1` port only.
5. `check_local_public_auth.py` (already proven against loopback), then —
   only after separate approval — `check_remote_public_auth.py --confirm`.

Shutdown is the reverse: stop each tunnel process first (revokes public
reachability immediately), then gracefully stop each peer
(`ManagedServer.stop()`'s existing graceful→forced→cancel ladder,
unchanged by `--public`), then re-run `check_port_release.py`.

## Pre-flight checklist (run before ever requesting Gate A2 approval)

- [x] `check_local_public_auth.py [police|thief]` passes (real, run this
      session, localhost only).
- [ ] `check_public_endpoint.py <intended-url>` passes (development-workspace
      script, not included in this standalone package).
- [ ] `check_peer_auth.py` passes (development-workspace script, not included
      in this standalone package).
- [ ] `check_port_release.py` shows no orphans (development-workspace script,
      not included in this standalone package).
- [ ] A real tunnel tool is installed and verified (not yet — see the Gate A
      read-only preflight report).
- [ ] Your explicit written approval for Gate A2 (actually starting a tunnel).

Readiness remains `LOCAL_READY`. This document does not raise readiness by
itself — see `_post4b_supplementary_evidence/audit/PROGRESS.md`.

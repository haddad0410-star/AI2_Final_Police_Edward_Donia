"""Gate A1: builds the auth + rate-limit stack for ``--public`` mode. Split
out of ``game_runner.py`` to stay under the 150-line cap.

Auth stays ASGI-level (``BearerAuthMiddleware``, via ``http_app(middleware=
...)``) -- it must guard session establishment itself, before any MCP
message is even parsed. Rate limiting (Gate A1 correction) is FastMCP
protocol-level (``McpRateLimitMiddleware``, via ``FastMCP.add_middleware``),
so it counts real logical tool calls, not raw HTTP transport frames -- see
``infrastructure/mcp_rate_limit_middleware.py``'s module docstring. An
unauthenticated request never reaches MCP dispatch at all, so it can never
consume a rate-limit slot either way.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP
from starlette.middleware import Middleware

from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.mcp_rate_limit_middleware import McpRateLimitMiddleware
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.config_loader import load_rate_limits


class PublicModeError(Exception):
    """Raised when ``--public`` cannot start safely -- fails closed, never
    silently falls back to unauthenticated mode."""


def resolve_public_tokens(public: bool) -> tuple[str | None, str | None]:
    """``--public`` with no (or a blank) ``PUBLIC_BIND_TOKEN`` is a startup
    error. ``OPPONENT_MCP_TOKEN`` is optional even in ``--public`` mode --
    the opponent may not require one. Neither value is logged here."""
    if not public:
        return None, None
    token = os.environ.get("PUBLIC_BIND_TOKEN", "").strip()
    if not token:
        raise PublicModeError("--public requires a nonempty PUBLIC_BIND_TOKEN environment variable")
    opponent_token = os.environ.get("OPPONENT_MCP_TOKEN", "").strip() or None
    return token, opponent_token


def build_public_middleware(mcp: FastMCP, public_token: str, config_dir: Path) -> list[Middleware]:
    """Registers the logical-operation rate limiter directly on ``mcp``
    (must happen before ``mcp.http_app()`` builds the ASGI app) and returns
    the ASGI middleware list (auth only) for ``http_app(middleware=...)``."""
    rate_config = load_rate_limits(config_dir / "rate_limits.json")
    gatekeeper = IncomingGatekeeper(rate_config)
    mcp.add_middleware(McpRateLimitMiddleware(gatekeeper, rate_config))
    return [Middleware(BearerAuthMiddleware, expected_token=public_token)]

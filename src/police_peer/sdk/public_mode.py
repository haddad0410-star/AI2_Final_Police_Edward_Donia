"""Gate A1: builds the auth + rate-limit middleware stack for ``--public``
mode. Split out of ``game_runner.py`` to stay under the 150-line cap. Auth
runs first (outermost), so an unauthenticated/invalid-token request is
rejected before it ever consumes a rate-limit slot meant for legitimate
traffic -- verified empirically in ``tests/integration/test_public_mode_http.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

from starlette.middleware import Middleware

from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware
from police_peer.infrastructure.rate_limit_middleware import RateLimitMiddleware
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


def build_public_middleware(public_token: str, config_dir: Path) -> list[Middleware]:
    """Auth is checked first (outermost): an invalid/missing token is
    rejected before it can ever consume a rate-limit slot. Only requests
    that pass auth reach the Gatekeeper, which in turn only lets an
    admitted request reach the real FastMCP app/tool dispatch."""
    rate_config = load_rate_limits(config_dir / "rate_limits.json")
    gatekeeper = IncomingGatekeeper(rate_config)
    return [
        Middleware(BearerAuthMiddleware, expected_token=public_token),
        Middleware(RateLimitMiddleware, gatekeeper=gatekeeper),
    ]

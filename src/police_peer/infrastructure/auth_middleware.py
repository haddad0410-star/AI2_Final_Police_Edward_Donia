"""Gate A1: raw ASGI middleware enforcing ``Authorization: Bearer
<PUBLIC_BIND_TOKEN>`` on every HTTP request, before it ever reaches
FastMCP's own routing/tool dispatch. Applied via ``http_app(middleware=...)``
-- never inside an individual ``@mcp.tool`` function, so a rejected request
never invokes one. Only active in ``--public`` mode; ``ManagedServer`` still
independently refuses to bind anything but 127.0.0.1/localhost/::1
regardless of this middleware's presence.
"""

from __future__ import annotations

import hmac

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BearerAuthMiddleware:
    """Rejects any HTTP request whose ``Authorization`` header does not
    present the exact expected bearer token, via constant-time comparison.
    The rejection reason is one of a small fixed set of words -- never the
    presented or expected token value, in the response, in an exception, or
    anywhere else."""

    def __init__(self, app: ASGIApp, *, expected_token: str) -> None:
        self._app = app
        self._expected_token = expected_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        reason = self._check(dict(scope.get("headers", ())))
        if reason is not None:
            await JSONResponse(
                {"ok": False, "error": "unauthorized", "reason": reason}, status_code=401
            )(scope, receive, send)
            return
        await self._app(scope, receive, send)

    def _check(self, headers: dict[bytes, bytes]) -> str | None:
        raw = headers.get(b"authorization")
        if raw is None:
            return "missing_authorization"
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return "malformed_authorization"
        scheme, _, value = text.partition(" ")
        if scheme != "Bearer" or not value:
            return "malformed_authorization"
        if not hmac.compare_digest(value, self._expected_token):
            return "invalid_token"
        return None

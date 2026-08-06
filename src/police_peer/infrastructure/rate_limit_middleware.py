"""Gate A1: raw ASGI middleware applying :class:`IncomingGatekeeper` to the
public HTTP/MCP surface, before FastMCP's own routing/tool dispatch --
never inside an individual ``@mcp.tool`` function. A rejected request gets
an honest 429/503-style JSON response and the wrapped app is never called,
so a rejection can never reach a tool.
"""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from police_peer.services.incoming_gatekeeper import IncomingGatekeeper, OverloadedError


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, *, gatekeeper: IncomingGatekeeper) -> None:
        self._app = app
        self._gatekeeper = gatekeeper

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        try:
            async with self._gatekeeper.slot():
                await self._app(scope, receive, send)
        except OverloadedError as exc:
            await JSONResponse(
                {"ok": False, "error": "overloaded", "reason": exc.reason}, status_code=429
            )(scope, receive, send)

"""Gate A1 correction: FastMCP protocol-level rate-limit middleware, replacing
the earlier ASGI-level ``RateLimitMiddleware``.

The earlier ASGI middleware counted every raw HTTP request the streamable-HTTP
transport happens to use (session initialize, ``notifications/initialized``,
capability discovery, the real ``tools/call``, session teardown -- roughly 6
raw requests per one logical tool call). Appendix F Table 19's "30 requests
per minute" binding minimum is a logical-operation budget (the book's own
worked context is an outbound API-call Gatekeeper, e.g. one Gmail send = one
request), not a raw-transport-frame budget. Hooking ``on_call_tool`` instead
of the ASGI layer means exactly one accounting event per real tool invocation
(``negotiate``/``propose_config``/``receive_turn``/``submit_audit``/
``receive_control``), regardless of how many raw HTTP requests FastMCP's own
session plumbing needed underneath -- session/capability/teardown frames are
never charged against the budget, matching Appendix F's own scope (it says
nothing about transport internals).

``health`` is deliberately excluded from accounting: it is a liveness/
readiness probe (used by ``wait_for_health`` during startup, potentially many
times), not one of the game-protocol operations Appendix F's Gatekeeper table
is about.

Auth stays entirely at the ASGI level (``auth_middleware.py``) -- unchanged,
since it must guard session establishment itself, not just tool calls.
"""

from __future__ import annotations

from fastmcp.server.middleware import Middleware
from mcp import McpError
from mcp.types import ErrorData

from police_peer.services.incoming_gatekeeper import IncomingGatekeeper, OverloadedError
from police_peer.shared.rate_limits_model import RateLimitsConfig

#: Distinct from FastMCP's own built-in RateLimitingMiddleware's -32000, so a
#: client can unambiguously recognize this specific error and choose to
#: retry (see ``infrastructure/mcp_client.py``'s bounded backoff).
OVERLOAD_ERROR_CODE = -32001

#: Tool calls that are liveness/readiness probes, not logical game
#: operations -- excluded from the rate/concurrency budget entirely.
_UNMETERED_TOOLS = frozenset({"health"})


class McpOverloadError(McpError):
    """Raised from ``on_call_tool`` when the incoming Gatekeeper rejects a
    logical operation; carries ``retry_after_seconds`` (the binding backoff
    minimum) so a well-behaved client can retry exactly once per Appendix F's
    own retry/backoff minimums rather than giving up immediately."""

    def __init__(self, reason: str, retry_after_seconds: float) -> None:
        super().__init__(
            ErrorData(
                code=OVERLOAD_ERROR_CODE,
                message=f"overloaded: {reason}",
                data={"reason": reason, "retry_after_seconds": retry_after_seconds},
            )
        )


class McpRateLimitMiddleware(Middleware):
    """FastMCP protocol-level middleware (registered via
    ``FastMCP.add_middleware``, NOT the ASGI ``http_app(middleware=...)``
    list) -- counts exactly one logical operation per real ``tools/call``
    dispatch, before the tool body runs."""

    def __init__(self, gatekeeper: IncomingGatekeeper, config: RateLimitsConfig) -> None:
        self._gatekeeper = gatekeeper
        self._retry_after = float(config.retry_backoff_sec)

    async def on_call_tool(self, context, call_next):
        if context.message.name in _UNMETERED_TOOLS:
            return await call_next(context)
        try:
            async with self._gatekeeper.slot():
                return await call_next(context)
        except OverloadedError as exc:
            raise McpOverloadError(exc.reason, self._retry_after) from exc

"""Minimal real FastMCP HTTP client calls to the opponent peer.

Every function here opens its own short-lived Client connection -- no shared
mutable client state between calls, and definitely none shared with the
opponent's own process. ``token``, when given, is presented as
``Authorization: Bearer <token>`` (Gate A1: the opponent's own
``OPPONENT_MCP_TOKEN``, needed only when that opponent runs in ``--public``
mode) -- never logged, never included in any raised exception's message.
"""

from __future__ import annotations

import asyncio

import anyio
import httpx
from fastmcp import Client
from fastmcp.client.auth.bearer import BearerAuth
from fastmcp.exceptions import ClientError, ToolError
from mcp.shared.exceptions import McpError

from police_peer.infrastructure.mcp_rate_limit_middleware import OVERLOAD_ERROR_CODE

#: FastMCP wraps unreachable-peer failures (connection refused, DNS, etc.) in
#: a plain RuntimeError as well as the more specific types below -- all mean
#: "the opponent could not be reached," never a bug in our own code.
#: httpx.TransportError (not the builtin TimeoutError) is what httpx actually
#: raises for ReadTimeout/ConnectTimeout/ConnectError; anyio.ClosedResourceError/
#: BrokenResourceError/EndOfStream are what surface when a peer's process exits
#: mid-response (a real, observed failure mode: an on-demand-binding opponent
#: whose server dies partway through an SSE stream) -- found 2026-08-17 when an
#: uncaught httpx.ReadTimeout crashed this peer's whole process instead of
#: failing that one call gracefully, the same class of gap already fixed once
#: this session for an uncaught 401 during health polling.
_CONNECTION_FAILURES = (
    OSError,
    TimeoutError,
    ClientError,
    RuntimeError,
    httpx.TransportError,
    anyio.ClosedResourceError,
    anyio.BrokenResourceError,
    anyio.EndOfStream,
)

#: Appendix F Table 19's own binding minimums (status "minimum" -- "absent
#: explicit agreement, the example value is the mandatory default"): a
#: well-behaved client honors AT LEAST a 5-second backoff and allows itself
#: AT LEAST 3 retries before giving up on a legitimate overload response.
DEFAULT_RETRY_BACKOFF_SEC = 5.0
DEFAULT_MAX_RETRIES = 3

#: The MCP SDK's generic ``tools/call`` exception handler
#: (``mcp/server/lowlevel/server.py``: ``except Exception as e: return
#: self._make_error_result(str(e))``) flattens ANY exception raised from
#: server-side middleware -- including ``McpOverloadError`` -- into a plain
#: ``isError=True`` tool result; the client only ever sees a
#: ``fastmcp.exceptions.ToolError`` carrying the stringified message, never
#: the original ``McpError`` with its structured code/data (confirmed by
#: direct inspection of the installed package and by a real authenticated
#: two-process series). These are the exact two messages
#: ``McpOverloadError`` can produce (see ``incoming_gatekeeper.py``'s
#: ``OverloadedError`` reasons) -- an EXACT allowlist, never a substring or
#: prefix match, so a validation/auth/tamper/schema/unknown-tool
#: ``ToolError`` is never misclassified as a retryable overload.
_OVERLOAD_TOOL_ERROR_MESSAGES = frozenset(
    {"overloaded: rate_limit_exceeded", "overloaded: queue_depth_exceeded"}
)


class PeerUnavailableError(Exception):
    """Raised when the opponent cannot be reached within the given timeout."""


def _is_connection_timeout(exc: McpError) -> bool:
    """True only for a client-side timeout waiting on ANY response (session
    read timeout or a raw ``httpx.ConnectTimeout``) -- the only two sites in
    the installed mcp/fastmcp packages that raise ``McpError`` with this
    exact code (verified against site-packages: ``mcp/shared/session.py``
    and ``fastmcp/utilities/exceptions.py``). Every other ``McpError`` either
    uses a different explicit code or forwards the OPPONENT's own real
    JSON-RPC error code -- a genuine remote/application fault, never
    reclassified as connectivity here."""
    return exc.error.code == httpx.codes.REQUEST_TIMEOUT


def _is_overload_tool_error(exc: ToolError) -> bool:
    """True only for the exact flattened overload message text -- see the
    module-level note on ``_OVERLOAD_TOOL_ERROR_MESSAGES`` above."""
    return str(exc) in _OVERLOAD_TOOL_ERROR_MESSAGES


def _retry_after(exc: McpError) -> float:
    data = exc.error.data
    if isinstance(data, dict):
        value = data.get("retry_after_seconds")
        if isinstance(value, int | float):
            return float(value)
    return DEFAULT_RETRY_BACKOFF_SEC


async def _call(
    url: str, tool: str, arguments: dict, timeout_seconds: float, token: str | None = None
) -> dict:
    """A legitimate overload response is retried -- honoring the server's
    own ``retry_after_seconds`` hint when a structured ``McpError`` is
    actually delivered, else the binding-minimum default backoff (the real
    ``tools/call`` path, see ``_OVERLOAD_TOOL_ERROR_MESSAGES``) -- up to
    ``DEFAULT_MAX_RETRIES`` times, Appendix F Table 19's own binding minimum
    retry count. Never retried indefinitely: once exhausted, this becomes an
    ordinary ``PeerUnavailableError``, the same outcome as any other
    opponent-trouble case the rest of this codebase already knows how to
    handle gracefully. A non-overload ``ToolError`` (validation, auth,
    tamper, schema, unknown-tool, ...) is never retried."""
    auth = BearerAuth(token) if token else None
    attempts = 0
    while True:
        try:
            async with Client(url, timeout=timeout_seconds, auth=auth) as client:
                result = await client.call_tool(tool, arguments)
            return result.data
        except _CONNECTION_FAILURES as exc:
            raise PeerUnavailableError(f"peer at {url} did not respond: {exc}") from exc
        except ToolError as exc:
            if _is_overload_tool_error(exc) and attempts < DEFAULT_MAX_RETRIES:
                attempts += 1
                await asyncio.sleep(DEFAULT_RETRY_BACKOFF_SEC)
                continue
            if _is_overload_tool_error(exc):
                raise PeerUnavailableError(
                    f"peer at {url} stayed overloaded after {attempts} retries"
                ) from exc
            raise PeerUnavailableError(f"peer at {url} rejected the call: {exc}") from exc
        except McpError as exc:
            if exc.error.code == OVERLOAD_ERROR_CODE and attempts < DEFAULT_MAX_RETRIES:
                attempts += 1
                await asyncio.sleep(_retry_after(exc))
                continue
            if exc.error.code == OVERLOAD_ERROR_CODE:
                raise PeerUnavailableError(
                    f"peer at {url} stayed overloaded after {attempts} retries"
                ) from exc
            if not _is_connection_timeout(exc):
                raise
            raise PeerUnavailableError(f"peer at {url} did not respond: {exc}") from exc


async def call_health(url: str, timeout_seconds: float = 5.0, token: str | None = None) -> dict:
    return await _call(url, "health", {}, timeout_seconds, token)


async def call_negotiate(
    url: str, message: dict, timeout_seconds: float = 5.0, token: str | None = None
) -> dict:
    return await _call(url, "negotiate", {"message": message}, timeout_seconds, token)


async def call_propose_config(
    url: str, message: dict, timeout_seconds: float = 5.0, token: str | None = None
) -> dict:
    return await _call(url, "propose_config", {"message": message}, timeout_seconds, token)


async def call_receive_turn(
    url: str, message: dict, timeout_seconds: float = 30.0, token: str | None = None
) -> dict:
    return await _call(url, "receive_turn", {"message": message}, timeout_seconds, token)


async def call_submit_audit(
    url: str, message: dict, timeout_seconds: float = 30.0, token: str | None = None
) -> dict:
    """The wire argument name is ``payload`` (matching
    ``_post4b_supplementary_evidence/audit/protocol_contract.md``'s ``submit_audit(payload:
    dict)`` -- a real cross-repo mismatch found and fixed post-Batch-4B: this
    tool went unused in real gameplay until the bilateral result-agreement
    fix first actually invoked it over real HTTP)."""
    return await _call(url, "submit_audit", {"payload": message}, timeout_seconds, token)


async def call_receive_control(
    url: str, message: dict, timeout_seconds: float = 30.0, token: str | None = None
) -> dict:
    return await _call(url, "receive_control", {"message": message}, timeout_seconds, token)


async def wait_for_health(
    url: str, attempts: int, delay_seconds: float, token: str | None = None
) -> dict:
    """Poll health with bounded retries; raises PeerUnavailableError if the
    opponent never comes up -- never hangs forever."""
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return await call_health(url, timeout_seconds=delay_seconds, token=token)
        except PeerUnavailableError as exc:
            last_error = exc
            await asyncio.sleep(delay_seconds)
    raise PeerUnavailableError(f"peer at {url} never became healthy: {last_error}")

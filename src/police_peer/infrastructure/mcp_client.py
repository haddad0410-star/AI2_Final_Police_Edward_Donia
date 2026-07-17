"""Minimal real FastMCP HTTP client calls to the opponent peer.

Every function here opens its own short-lived Client connection -- no shared
mutable client state between calls, and definitely none shared with the
opponent's own process.
"""

from __future__ import annotations

import asyncio

from fastmcp import Client
from fastmcp.exceptions import ClientError

#: FastMCP wraps unreachable-peer failures (connection refused, DNS, etc.) in
#: a plain RuntimeError as well as the more specific types below -- all mean
#: "the opponent could not be reached," never a bug in our own code.
_CONNECTION_FAILURES = (OSError, TimeoutError, ClientError, RuntimeError)


class PeerUnavailableError(Exception):
    """Raised when the opponent cannot be reached within the given timeout."""


async def _call(url: str, tool: str, arguments: dict, timeout_seconds: float) -> dict:
    try:
        async with Client(url, timeout=timeout_seconds) as client:
            result = await client.call_tool(tool, arguments)
    except _CONNECTION_FAILURES as exc:
        raise PeerUnavailableError(f"peer at {url} did not respond: {exc}") from exc
    return result.data


async def call_health(url: str, timeout_seconds: float = 5.0) -> dict:
    return await _call(url, "health", {}, timeout_seconds)


async def call_negotiate(url: str, message: dict, timeout_seconds: float = 5.0) -> dict:
    return await _call(url, "negotiate", {"message": message}, timeout_seconds)


async def call_propose_config(url: str, message: dict, timeout_seconds: float = 5.0) -> dict:
    return await _call(url, "propose_config", {"message": message}, timeout_seconds)


async def wait_for_health(url: str, attempts: int, delay_seconds: float) -> dict:
    """Poll health with bounded retries; raises PeerUnavailableError if the
    opponent never comes up -- never hangs forever."""
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return await call_health(url, timeout_seconds=delay_seconds)
        except PeerUnavailableError as exc:
            last_error = exc
            await asyncio.sleep(delay_seconds)
    raise PeerUnavailableError(f"peer at {url} never became healthy: {last_error}")

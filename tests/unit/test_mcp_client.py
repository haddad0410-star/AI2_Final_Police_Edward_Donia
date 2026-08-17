"""Regression coverage for mcp_client.py's McpError classification (Batch 4B
follow-up): a client-side connection/session timeout (McpError code=408,
httpx.codes.REQUEST_TIMEOUT) must be treated as PeerUnavailableError so
wait_for_health's bounded retry loop can recover from it; any OTHER McpError
(a genuine remote/application error) must propagate unchanged, never
silently swallowed. All tests here are monkeypatched/deterministic -- no
real sockets are opened, so there is nothing to leak or orphan.
"""

from __future__ import annotations

import asyncio

import anyio
import httpx
import pytest
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from police_peer.infrastructure import mcp_client as mc
from police_peer.infrastructure.mcp_client import PeerUnavailableError


class _FakeConnectCM:
    """Stands in for ``fastmcp.Client(url, timeout=...)`` -- raises ``exc``
    from ``__aenter__``, exactly where the real timeout surfaces."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __aenter__(self):
        raise self._exc

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _client_factory(exc: Exception):
    def _factory(url: str, timeout: float | None = None, auth=None):
        return _FakeConnectCM(exc)

    return _factory


def _timeout_error(
    message: str = "Timed out while waiting for response to InitializeRequest. Waited 5.0 seconds.",
) -> McpError:
    return McpError(ErrorData(code=httpx.codes.REQUEST_TIMEOUT, message=message))


def test_initialize_request_timeout_is_peer_unavailable(monkeypatch) -> None:
    """The exact failure from the Batch 4B regression: a session
    InitializeRequest timeout must become PeerUnavailableError, not crash
    the caller as a raw McpError."""
    monkeypatch.setattr(mc, "Client", _client_factory(_timeout_error()))
    with pytest.raises(PeerUnavailableError):
        asyncio.run(mc.call_health("http://x/mcp"))


def test_wait_for_health_retries_initialize_timeout_within_budget(monkeypatch) -> None:
    """wait_for_health must retry this specific failure like any other
    connection failure -- bounded, never hanging, never crashing."""
    monkeypatch.setattr(mc, "Client", _client_factory(_timeout_error()))
    with pytest.raises(PeerUnavailableError, match="never became healthy"):
        asyncio.run(mc.wait_for_health("http://x/mcp", attempts=3, delay_seconds=0.0))


def test_wait_for_health_recovers_once_the_timeout_stops(monkeypatch) -> None:
    """A transient InitializeRequest timeout that clears within the retry
    budget must let the caller proceed -- proves the retry loop, not just
    the classification, actually works end to end."""
    calls = {"n": 0}

    class _EventualClient:
        def __init__(self, url, timeout=None, auth=None):
            calls["n"] += 1

        async def __aenter__(self):
            if calls["n"] <= 2:
                raise _timeout_error()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, tool, arguments):
            class _Result:
                data = {"status": "ok"}

            return _Result()

    monkeypatch.setattr(mc, "Client", _EventualClient)
    result = asyncio.run(mc.wait_for_health("http://x/mcp", attempts=5, delay_seconds=0.0))
    assert result == {"status": "ok"}
    assert calls["n"] == 3


def test_genuinely_unreachable_peer_still_bounded(monkeypatch) -> None:
    """A plain connection-refused-style failure (unrelated to McpError) must
    still hit the SAME bounded retry policy, unchanged by this fix."""

    class _RefusingClient:
        def __init__(self, url, timeout=None, auth=None):
            pass

        async def __aenter__(self):
            raise OSError("connection refused")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(mc, "Client", _RefusingClient)
    with pytest.raises(PeerUnavailableError, match="never became healthy"):
        asyncio.run(mc.wait_for_health("http://x/mcp", attempts=3, delay_seconds=0.0))


def test_successful_health_call_unaffected(monkeypatch) -> None:
    """The ordinary success path (no exception at all) must be untouched by
    the new McpError branch."""

    class _OkClient:
        def __init__(self, url, timeout=None, auth=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, tool, arguments):
            class _Result:
                data = {"status": "ok", "role": "police"}

            return _Result()

    monkeypatch.setattr(mc, "Client", _OkClient)
    result = asyncio.run(mc.call_health("http://x/mcp"))
    assert result == {"status": "ok", "role": "police"}


def test_httpx_read_timeout_is_peer_unavailable(monkeypatch) -> None:
    """2026-08-17 regression: httpx.ReadTimeout is a subclass of
    httpx.TransportError, NOT the builtin TimeoutError -- it was falling
    through _CONNECTION_FAILURES entirely and crashing the whole process
    instead of failing this one call gracefully, against a real opponent
    whose server died mid-response."""
    monkeypatch.setattr(mc, "Client", _client_factory(httpx.ReadTimeout("timed out")))
    with pytest.raises(PeerUnavailableError):
        asyncio.run(mc.call_health("http://x/mcp"))


def test_anyio_closed_resource_error_is_peer_unavailable(monkeypatch) -> None:
    """2026-08-17 regression: a peer's process exiting mid-SSE-stream (an
    on-demand-binding opponent whose server dies partway through a response)
    surfaces as anyio.ClosedResourceError from the SSE reader, not any of
    the previously-caught types -- must become PeerUnavailableError, not an
    uncaught crash."""
    monkeypatch.setattr(mc, "Client", _client_factory(anyio.ClosedResourceError()))
    with pytest.raises(PeerUnavailableError):
        asyncio.run(mc.call_health("http://x/mcp"))


def test_non_timeout_mcp_error_is_not_swallowed(monkeypatch) -> None:
    """A genuine remote/application-level MCP error (e.g. the opponent's own
    real JSON-RPC error, a different code) must propagate as McpError --
    never silently reclassified as a mere connectivity issue."""
    real_error = McpError(ErrorData(code=-32601, message="Method not found"))
    monkeypatch.setattr(mc, "Client", _client_factory(real_error))
    with pytest.raises(McpError):
        asyncio.run(mc.call_health("http://x/mcp"))

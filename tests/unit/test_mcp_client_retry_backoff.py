"""Gate A1 correction: mcp_client.py's bounded retry/backoff on a real
overload response (``McpOverloadError``/``OVERLOAD_ERROR_CODE``) -- honors
the server's ``retry_after_seconds`` hint, retries at most
``DEFAULT_MAX_RETRIES`` times (Appendix F Table 19's own binding minimum
retry count), then gives up as an ordinary ``PeerUnavailableError`` -- never
retries indefinitely."""

from __future__ import annotations

import asyncio

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from police_peer.infrastructure import mcp_client as mc
from police_peer.infrastructure.mcp_client import DEFAULT_MAX_RETRIES, PeerUnavailableError
from police_peer.infrastructure.mcp_rate_limit_middleware import OVERLOAD_ERROR_CODE


def _overload_error(retry_after: float = 9.0) -> McpError:
    return McpError(
        ErrorData(
            code=OVERLOAD_ERROR_CODE,
            message="overloaded: rate_limit_exceeded",
            data={"reason": "rate_limit_exceeded", "retry_after_seconds": retry_after},
        )
    )


class _Result:
    data = {"status": "ok"}


def _recording_no_sleep(sleeps: list[float]):
    """A fake ``asyncio.sleep`` that records the requested delay and
    returns instantly, so these tests don't actually wait out real
    multi-second backoffs. Deliberately does NOT call the real
    ``asyncio.sleep`` -- ``mc.asyncio`` is the same module object as this
    test file's own ``asyncio`` import, so doing so would recurse into the
    patched function."""

    async def _fake(_seconds: float) -> None:
        sleeps.append(_seconds)

    return _fake


def _client_factory(fail_times: int, retry_after: float = 9.0):
    calls = {"n": 0}

    class _Client:
        def __init__(self, url, timeout=None, auth=None):
            calls["n"] += 1

        async def __aenter__(self):
            if calls["n"] <= fail_times:
                raise _overload_error(retry_after)
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, tool, arguments):
            return _Result()

    return _Client, calls


def test_overload_is_retried_and_eventually_succeeds(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(mc.asyncio, "sleep", _recording_no_sleep(sleeps))
    client_cls, calls = _client_factory(fail_times=2, retry_after=9.0)
    monkeypatch.setattr(mc, "Client", client_cls)

    result = asyncio.run(mc.call_health("http://x/mcp"))

    assert result == {"status": "ok"}
    assert calls["n"] == 3  # 2 failures + 1 success
    assert sleeps == [9.0, 9.0]


def test_overload_honors_the_server_retry_after_hint(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(mc.asyncio, "sleep", _recording_no_sleep(sleeps))
    client_cls, _ = _client_factory(fail_times=1, retry_after=2.5)
    monkeypatch.setattr(mc, "Client", client_cls)

    asyncio.run(mc.call_health("http://x/mcp"))

    assert sleeps == [2.5]


def test_overload_gives_up_after_the_binding_minimum_retry_count(monkeypatch) -> None:
    """Never retries indefinitely: exactly DEFAULT_MAX_RETRIES retries, then
    a bounded, ordinary PeerUnavailableError."""
    sleeps: list[float] = []
    monkeypatch.setattr(mc.asyncio, "sleep", _recording_no_sleep(sleeps))
    client_cls, calls = _client_factory(fail_times=999, retry_after=1.0)
    monkeypatch.setattr(mc, "Client", client_cls)

    with pytest.raises(PeerUnavailableError, match="stayed overloaded"):
        asyncio.run(mc.call_health("http://x/mcp"))

    assert calls["n"] == DEFAULT_MAX_RETRIES + 1  # 1 initial attempt + N retries
    assert len(sleeps) == DEFAULT_MAX_RETRIES

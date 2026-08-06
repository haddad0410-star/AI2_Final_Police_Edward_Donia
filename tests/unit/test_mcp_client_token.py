"""Gate A1: mcp_client.py's token handling -- BearerAuth added only when a
token is given; never serialized/echoed in any diagnostic output."""

from __future__ import annotations

import asyncio

from fastmcp.client.auth.bearer import BearerAuth

import police_peer.infrastructure.mcp_client as mc

TOKEN = "h" * 40


def test_no_token_means_no_auth_object(monkeypatch) -> None:
    captured = {}

    class _Recording:
        def __init__(self, url, timeout=None, auth=None):
            captured["auth"] = auth

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, tool, arguments):
            class _Result:
                data = {"status": "ok"}

            return _Result()

    monkeypatch.setattr(mc, "Client", _Recording)
    asyncio.run(mc.call_health("http://x/mcp"))
    assert captured["auth"] is None


def test_token_present_builds_a_real_bearer_auth(monkeypatch) -> None:
    captured = {}

    class _Recording:
        def __init__(self, url, timeout=None, auth=None):
            captured["auth"] = auth

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(self, tool, arguments):
            class _Result:
                data = {"status": "ok"}

            return _Result()

    monkeypatch.setattr(mc, "Client", _Recording)
    asyncio.run(mc.call_health("http://x/mcp", token=TOKEN))
    assert isinstance(captured["auth"], BearerAuth)


def test_bearer_auth_repr_never_reveals_the_token() -> None:
    auth = BearerAuth(TOKEN)
    assert TOKEN not in repr(auth)
    assert TOKEN not in str(auth.token)


def test_peer_unavailable_error_never_contains_the_token() -> None:
    class _Refusing:
        def __init__(self, url, timeout=None, auth=None):
            pass

        async def __aenter__(self):
            raise OSError("connection refused")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    import police_peer.infrastructure.mcp_client as mc_mod

    orig = mc_mod.Client
    mc_mod.Client = _Refusing
    try:
        try:
            asyncio.run(mc.call_health("http://x/mcp", token=TOKEN))
            raise AssertionError("expected PeerUnavailableError")
        except mc.PeerUnavailableError as exc:
            assert TOKEN not in str(exc)
    finally:
        mc_mod.Client = orig

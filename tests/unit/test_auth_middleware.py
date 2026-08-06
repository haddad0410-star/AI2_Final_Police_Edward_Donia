"""Gate A1: BearerAuthMiddleware, tested directly over ASGI (no real socket)."""

from __future__ import annotations

import asyncio

import httpx

from police_peer.infrastructure.auth_middleware import BearerAuthMiddleware

TOKEN = "a" * 40


async def _inner_app(scope, receive, send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _client() -> httpx.AsyncClient:
    app = BearerAuthMiddleware(_inner_app, expected_token=TOKEN)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_missing_authorization_is_rejected() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp")

    resp = asyncio.run(scenario())
    assert resp.status_code == 401
    assert resp.json()["reason"] == "missing_authorization"


def test_wrong_scheme_is_rejected() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp", headers={"Authorization": f"Basic {TOKEN}"})

    resp = asyncio.run(scenario())
    assert resp.status_code == 401
    assert resp.json()["reason"] == "malformed_authorization"


def test_blank_bearer_value_is_rejected() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp", headers={"Authorization": "Bearer "})

    resp = asyncio.run(scenario())
    assert resp.status_code == 401
    assert resp.json()["reason"] == "malformed_authorization"


def test_wrong_token_is_rejected() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp", headers={"Authorization": "Bearer " + "b" * 40})

    resp = asyncio.run(scenario())
    assert resp.status_code == 401
    assert resp.json()["reason"] == "invalid_token"


def test_correct_token_is_accepted() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})

    resp = asyncio.run(scenario())
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_rejection_response_never_contains_the_expected_token() -> None:
    async def scenario() -> httpx.Response:
        async with _client() as client:
            return await client.get("/mcp", headers={"Authorization": "Bearer " + "b" * 40})

    resp = asyncio.run(scenario())
    assert TOKEN not in resp.text


def test_non_http_scope_passes_through_untouched() -> None:
    events: list[dict] = []

    async def inner(scope, receive, send) -> None:
        events.append(scope)

    async def scenario() -> None:
        app = BearerAuthMiddleware(inner, expected_token=TOKEN)
        await app({"type": "lifespan"}, None, None)

    asyncio.run(scenario())
    assert events == [{"type": "lifespan"}]

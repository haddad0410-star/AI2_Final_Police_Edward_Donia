"""Gate A1: RateLimitMiddleware -- a rejected request must never reach the
wrapped app (i.e. never invoke an MCP tool)."""

from __future__ import annotations

import asyncio

import httpx

from police_peer.infrastructure.rate_limit_middleware import RateLimitMiddleware
from police_peer.services.incoming_gatekeeper import IncomingGatekeeper
from police_peer.shared.rate_limits_model import RateLimitsConfig


def _config(**overrides) -> RateLimitsConfig:
    base = {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    base.update(overrides)
    return RateLimitsConfig(**base)


def test_admitted_request_reaches_the_app() -> None:
    calls: list[str] = []

    async def inner(scope, receive, send) -> None:
        calls.append("invoked")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def scenario() -> httpx.Response:
        app = RateLimitMiddleware(inner, gatekeeper=IncomingGatekeeper(_config()))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/mcp")

    resp = asyncio.run(scenario())
    assert resp.status_code == 200
    assert calls == ["invoked"]


def test_rejected_request_never_invokes_the_app() -> None:
    calls: list[str] = []

    async def inner(scope, receive, send) -> None:
        calls.append("invoked")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def scenario() -> httpx.Response:
        gk = IncomingGatekeeper(_config(requests_per_minute=1000))
        app = RateLimitMiddleware(inner, gatekeeper=gk)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            gk._queue_depth = gk._config.queue_depth  # force overload
            return await client.get("/mcp")

    resp = asyncio.run(scenario())
    assert resp.status_code == 429
    assert calls == []


def test_non_http_scope_passes_through_untouched() -> None:
    events: list[dict] = []

    async def inner(scope, receive, send) -> None:
        events.append(scope)

    async def scenario() -> None:
        app = RateLimitMiddleware(inner, gatekeeper=IncomingGatekeeper(_config()))
        await app({"type": "lifespan"}, None, None)

    asyncio.run(scenario())
    assert events == [{"type": "lifespan"}]

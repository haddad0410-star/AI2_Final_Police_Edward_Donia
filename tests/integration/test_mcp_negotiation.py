"""Real HTTP FastMCP negotiation tests -- server run in-process as an asyncio
task, client calls made over actual HTTP to 127.0.0.1. No mocks."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_client import (
    PeerUnavailableError,
    call_health,
    call_negotiate,
    call_propose_config,
    wait_for_health,
)
from police_peer.infrastructure.mcp_server import build_peer_server, run_server_until_cancelled

HOST = "127.0.0.1"
CONFIG_HASH = "a" * 64


async def _start(port: int, config_hash: str = CONFIG_HASH):
    mcp, inbox = build_peer_server(Role.POLICE, config_hash)
    task = asyncio.create_task(run_server_until_cancelled(mcp, HOST, port))
    await asyncio.sleep(0.3)
    return task, inbox


async def _stop(task: asyncio.Task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def _url(port: int) -> str:
    return f"http://{HOST}:{port}/mcp"


def test_health_check_over_real_http() -> None:
    async def scenario() -> None:
        task, _ = await _start(18901)
        try:
            result = await call_health(_url(18901))
            assert result["status"] == "ok"
            assert result["role"] == "police"
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_matching_config_negotiation_succeeds() -> None:
    async def scenario() -> None:
        task, _ = await _start(18902)
        try:
            ack = await call_propose_config(
                _url(18902),
                {"envelope": {"correlation_id": "c1"}, "config_sha256": CONFIG_HASH},
            )
            assert ack["accepted"] is True
            assert ack["config_sha256_match"] is True
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_mismatched_config_refuses_to_proceed() -> None:
    async def scenario() -> None:
        task, _ = await _start(18903)
        try:
            ack = await call_propose_config(
                _url(18903),
                {"envelope": {"correlation_id": "c1"}, "config_sha256": "b" * 64},
            )
            assert ack["accepted"] is False
            assert ack["config_sha256_match"] is False
            assert ack["reason"]
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_malformed_negotiation_fails_cleanly() -> None:
    async def scenario() -> None:
        task, _ = await _start(18904)
        try:
            result = await call_negotiate(_url(18904), {"nonsense": True})
            assert result["ok"] is False
            assert result["error_code"] == "MALFORMED"
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_unavailable_peer_times_out_cleanly() -> None:
    async def scenario() -> None:
        with pytest.raises(PeerUnavailableError):
            await wait_for_health(_url(18999), attempts=2, delay_seconds=0.2)

    asyncio.run(scenario())


def test_duplicate_identical_negotiation_is_idempotent() -> None:
    async def scenario() -> None:
        task, _ = await _start(18905)
        try:
            message = {
                "envelope": {"correlation_id": "dup-1"},
                "group_id": "edward-donia",
            }
            first = await call_negotiate(_url(18905), message)
            second = await call_negotiate(_url(18905), message)
            assert first["ok"] is True
            assert second["ok"] is True
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_conflicting_duplicate_is_rejected() -> None:
    async def scenario() -> None:
        task, _ = await _start(18906)
        try:
            first = await call_negotiate(
                _url(18906),
                {"envelope": {"correlation_id": "dup-2"}, "group_id": "edward-donia"},
            )
            second = await call_negotiate(
                _url(18906),
                {"envelope": {"correlation_id": "dup-2"}, "group_id": "someone-else"},
            )
            assert first["ok"] is True
            assert second["ok"] is False
            assert second["error_code"] == "CONFLICTING_DUPLICATE"
        finally:
            await _stop(task)

    asyncio.run(scenario())

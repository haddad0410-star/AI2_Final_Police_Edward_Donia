"""Real HTTP test for push_negotiate -- server run in-process, client calls
made over actual HTTP to 127.0.0.1. No mocks. Regression coverage for the
2026-08-17 finding: run_series_headless never called negotiate at all, so a
compliant opponent that requires a signed agreement before accepting real
turns would never receive one."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_server import build_peer_server, run_server_until_cancelled
from police_peer.sdk.negotiate_push import push_negotiate
from police_peer.shared.config_loader import load_private_config, load_shared_config

HOST = "127.0.0.1"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


async def _start(port: int):
    mcp, inbox = build_peer_server(Role.POLICE, "a" * 64)
    task = asyncio.create_task(run_server_until_cancelled(mcp, HOST, port))
    await asyncio.sleep(0.3)
    return task, inbox


async def _stop(task: asyncio.Task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def test_push_negotiate_lands_a_real_signed_agreement() -> None:
    async def scenario():
        task, inbox = await _start(8951)
        try:
            shared = load_shared_config(FIXTURES / "valid_shared_game.json")
            private = load_private_config(FIXTURES / "valid_private_game.toml")
            await push_negotiate(shared, private, f"http://{HOST}:8951/mcp", "police", None)
            assert inbox.declarations.qsize() == 1
            declared = inbox.declarations.get_nowait()
            assert declared["group_id"] == private.game.group_id
            assert declared["role"] == "police"
            assert "signature" in declared and "terms" in declared and "nonce" in declared
        finally:
            await _stop(task)

    asyncio.run(scenario())


def test_push_negotiate_never_raises_on_unreachable_opponent() -> None:
    async def scenario():
        shared = load_shared_config(FIXTURES / "valid_shared_game.json")
        private = load_private_config(FIXTURES / "valid_private_game.toml")
        # Nothing listens on this port -- must not raise (best-effort only).
        await push_negotiate(shared, private, f"http://{HOST}:8952/mcp", "police", None)

    asyncio.run(scenario())

"""Phase 6: real HTTP FastMCP calls to the game-phase tools (no mocks).

Proves receive_turn, its receive_move alias, submit_audit and receive_control
are wired to the shared validation path and reach the bounded inbox.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastmcp import Client

from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerState, PeerStateMachine
from police_peer.infrastructure.mcp_server import build_peer_server, run_server_until_cancelled

HOST = "127.0.0.1"
GAME_UID = "uid-http"
CONFIG_HASH = "a" * 64


def _turn(message_type: str, step: int, seq: int) -> dict:
    return {
        "message_type": message_type,
        "envelope": {
            "game_uid": GAME_UID,
            "sender": "thief",
            "sub_game_number": 1,
            "step": step,
            "sequence_id": seq,
        },
    }


async def _start(port: int):
    machine = PeerStateMachine(initial=PeerState.WAITING)
    mcp, inbox = build_peer_server(Role.POLICE, CONFIG_HASH, game_uid=GAME_UID, machine=machine)
    task = asyncio.create_task(run_server_until_cancelled(mcp, HOST, port))
    await asyncio.sleep(0.3)
    return task, inbox


async def _stop(task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def test_receive_turn_and_move_alias_share_path() -> None:
    async def scenario() -> None:
        task, inbox = await _start(18921)
        try:
            url = f"http://{HOST}:18921/mcp"
            async with Client(url, timeout=5.0) as client:
                r1 = await client.call_tool("receive_turn", {"message": _turn("commitment", 0, 0)})
                r2 = await client.call_tool(
                    "receive_move", {"message": _turn("commitment_ack", 0, 1)}
                )
                r3 = await client.call_tool(
                    "submit_audit",
                    {"message": {"envelope": _turn("reveal", 0, 2)["envelope"], "records": []}},
                )
                r4 = await client.call_tool(
                    "receive_control", {"message": {"kind": "status", "status_text": "ok"}}
                )
            assert r1.data["ok"] is True
            assert r2.data["ok"] is True  # alias reaches the same handler
            assert r3.data["ok"] is True
            assert r4.data["ok"] is True
            assert len(inbox.turn_messages) == 2
            assert len(inbox.audits) == 1
            assert len(inbox.controls) == 1
        finally:
            await _stop(task)

    asyncio.run(scenario())

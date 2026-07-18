"""Coverage for HttpOpponentTransport parsing + unreachable handling.

The network call is monkeypatched (test-only) so we exercise the reveal-parsing
and failure paths without a real second peer.
"""

from __future__ import annotations

import asyncio

from police_peer.infrastructure import http_transport as ht
from police_peer.infrastructure.http_transport import HttpOpponentTransport
from police_peer.infrastructure.inbox import PeerInbox
from police_peer.infrastructure.mcp_client import PeerUnavailableError
from police_peer.services.transport import OpponentReveal, TechnicalFailure

GRID = 7


def _inbox_with_opponent_turn() -> PeerInbox:
    inbox = PeerInbox()
    inbox.turn_messages.append(
        {"message_type": "reveal", "reveal": {"move": "S", "hint": "west", "win_claim": False}}
    )
    grid = [[0.3 for _ in range(GRID)] for _ in range(GRID)]
    inbox.turn_messages.append({"message_type": "scent", "grid": grid})
    inbox.turn_messages.append({"message_type": "capture_response", "caught": True})
    return inbox


def test_exchange_turn_parses_opponent_reveal(monkeypatch) -> None:
    async def _noop(url, message, timeout_seconds=30.0):
        return {"ok": True}

    monkeypatch.setattr(ht, "call_receive_turn", _noop)
    inbox = _inbox_with_opponent_turn()
    transport = HttpOpponentTransport("http://x/mcp", inbox, grid_size=GRID)

    result = asyncio.run(transport.exchange_turn({"c": 1}, {"r": 1}))
    assert isinstance(result, OpponentReveal)
    assert result.move == "S"
    assert result.claim_response is True
    assert result.scent_grid[0][0] == 0.3


def test_exchange_turn_unreachable_opponent(monkeypatch) -> None:
    async def _boom(url, message, timeout_seconds=30.0):
        raise PeerUnavailableError("refused")

    monkeypatch.setattr(ht, "call_receive_turn", _boom)
    transport = HttpOpponentTransport("http://x/mcp", PeerInbox(), grid_size=GRID)
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert isinstance(result, TechnicalFailure)
    assert "unreachable" in result.reason


def test_exchange_turn_no_reveal_times_out(monkeypatch) -> None:
    async def _noop(url, message, timeout_seconds=30.0):
        return {"ok": True}

    monkeypatch.setattr(ht, "call_receive_turn", _noop)
    transport = HttpOpponentTransport(
        "http://x/mcp", PeerInbox(), grid_size=GRID, poll_interval=0.0, max_polls=2
    )
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert isinstance(result, TechnicalFailure)
    assert "poll budget" in result.reason

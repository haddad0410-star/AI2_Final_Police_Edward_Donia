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
    # ``claim_response`` (like ``scent_grid``) travels bundled inside the
    # ``reveal`` body -- never as a separate message (Batch 3.5 Task 9,
    # defect H addendum: this mirrors the earlier scent-grid fix, B1).
    inbox = PeerInbox()
    grid = [[0.3 for _ in range(GRID)] for _ in range(GRID)]
    inbox.turn_messages.append(
        {
            "message_type": "reveal",
            "reveal": {
                "move": "S",
                "hint": "west",
                "win_claim": False,
                "scent_grid": grid,
                "claim_response": True,
            },
        }
    )
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


def test_progress_distinguishes_commit_rejected_from_reveal_rejected(monkeypatch) -> None:
    """Batch 4B GUI protocol-status fix: two different real failure points
    must produce two different real progress signatures -- proves the three
    booleans are read from where the exchange actually stopped, never
    hardcoded or collapsed onto a single pass/fail flag."""

    async def _reject_commit(url, message, timeout_seconds=30.0):
        return {"ok": False}

    monkeypatch.setattr(ht, "call_receive_turn", _reject_commit)
    transport = HttpOpponentTransport("http://x/mcp", PeerInbox(), grid_size=GRID)
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert (result.commit_sent, result.commit_acked, result.reveal_sent) == (True, False, False)

    calls = {"n": 0}

    async def _reject_reveal(url, message, timeout_seconds=30.0):
        calls["n"] += 1
        return {"ok": calls["n"] == 1}

    monkeypatch.setattr(ht, "call_receive_turn", _reject_reveal)
    transport = HttpOpponentTransport("http://x/mcp", PeerInbox(), grid_size=GRID)
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert (result.commit_sent, result.commit_acked, result.reveal_sent) == (True, True, True)


def test_progress_unreachable_on_commit_vs_unreachable_on_reveal(monkeypatch) -> None:
    """A connection failure on the FIRST call (commit) must report LESS
    progress than one on the SECOND call (reveal) -- both raise the same
    ``PeerUnavailableError`` type, so this can only pass if progress is
    tracked live, not derived from the exception type/message alone."""

    async def _boom_first(url, message, timeout_seconds=30.0):
        raise PeerUnavailableError("refused")

    monkeypatch.setattr(ht, "call_receive_turn", _boom_first)
    transport = HttpOpponentTransport("http://x/mcp", PeerInbox(), grid_size=GRID)
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert (result.commit_sent, result.commit_acked, result.reveal_sent) == (False, False, False)

    calls = {"n": 0}

    async def _boom_second(url, message, timeout_seconds=30.0):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"ok": True}
        raise PeerUnavailableError("refused")

    monkeypatch.setattr(ht, "call_receive_turn", _boom_second)
    transport = HttpOpponentTransport("http://x/mcp", PeerInbox(), grid_size=GRID)
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert (result.commit_sent, result.commit_acked, result.reveal_sent) == (True, True, False)


def test_progress_full_before_reveal_poll_timeout(monkeypatch) -> None:
    """A timed-out wait for the opponent's OWN reveal still means our own
    commit+reveal genuinely went through -- all three must be True even
    though the overall outcome is a TechnicalFailure."""

    async def _noop(url, message, timeout_seconds=30.0):
        return {"ok": True}

    monkeypatch.setattr(ht, "call_receive_turn", _noop)
    transport = HttpOpponentTransport(
        "http://x/mcp", PeerInbox(), grid_size=GRID, poll_interval=0.0, max_polls=2
    )
    result = asyncio.run(transport.exchange_turn({}, {}))
    assert (result.commit_sent, result.commit_acked, result.reveal_sent) == (True, True, True)

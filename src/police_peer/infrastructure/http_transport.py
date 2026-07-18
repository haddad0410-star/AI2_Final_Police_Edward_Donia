"""Real-HTTP opponent transport (Batch 2, Phase 9 production seam).

Sends our sealed commitment and reveal to the opponent's ``receive_turn`` tool,
then assembles the opponent's :class:`OpponentReveal` from the messages the
opponent delivered into OUR bounded inbox. If the opponent is unreachable or no
matching reveal arrives before a bounded number of polls, a
:class:`TechnicalFailure` is returned rather than hanging.

NOTE: this is the structural production seam. It has NOT been exercised against
a live second peer in this task (see docs/LIMITATIONS.md); cross-process
validation is a later, human-run step.
"""

from __future__ import annotations

import asyncio

from police_peer.infrastructure.inbox import PeerInbox
from police_peer.infrastructure.mcp_client import PeerUnavailableError, call_receive_turn
from police_peer.services.transport import OpponentReveal, TechnicalFailure


class HttpOpponentTransport:
    """Drives one commit+reveal round-trip over real FastMCP HTTP."""

    def __init__(
        self,
        opponent_url: str,
        inbox: PeerInbox,
        *,
        poll_interval: float = 0.1,
        max_polls: int = 300,
        grid_size: int = 7,
    ) -> None:
        self._url = opponent_url
        self._inbox = inbox
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._grid_size = grid_size

    async def exchange_turn(
        self, commitment: dict, reveal: dict
    ) -> OpponentReveal | TechnicalFailure:
        """Deliver our messages, then await the opponent's public reveal."""
        try:
            await call_receive_turn(self._url, commitment)
            await call_receive_turn(self._url, reveal)
        except PeerUnavailableError as exc:
            return TechnicalFailure(f"opponent unreachable: {exc}")
        return await self._await_opponent_reveal()

    async def _await_opponent_reveal(self) -> OpponentReveal | TechnicalFailure:
        for _ in range(self._max_polls):
            message = self._pop_reveal()
            if message is not None:
                return self._to_reveal(message)
            await asyncio.sleep(self._poll_interval)
        return TechnicalFailure("no opponent reveal received within poll budget")

    def _pop_reveal(self) -> dict | None:
        for index, message in enumerate(self._inbox.turn_messages):
            if message.get("message_type") == "reveal":
                del self._inbox.turn_messages[index]
                return message
        return None

    def _to_reveal(self, message: dict) -> OpponentReveal:
        body = message.get("reveal", {})
        barrier = body.get("barrier_placed")
        return OpponentReveal(
            move=body.get("move"),
            hint=body.get("hint", ""),
            scent_grid=self._latest_scent_grid(),
            barrier=tuple(barrier) if barrier else None,
            claim_response=self._latest_claim_response(),
            win_claim=bool(body.get("win_claim", False)),
        )

    def _latest_scent_grid(self) -> tuple[tuple[float, ...], ...]:
        for message in reversed(self._inbox.turn_messages):
            if message.get("message_type") == "scent" and "grid" in message:
                return tuple(tuple(row) for row in message["grid"])
        return tuple(tuple(0.0 for _ in range(self._grid_size)) for _ in range(self._grid_size))

    def _latest_claim_response(self) -> bool | None:
        for message in reversed(self._inbox.turn_messages):
            if message.get("message_type") == "capture_response":
                return bool(message.get("caught"))
        return None

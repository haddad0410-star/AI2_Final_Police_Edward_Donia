"""Real-HTTP opponent transport (Batch 2, Phase 9 production seam).

Sends our sealed commitment and reveal to the opponent's ``receive_turn`` tool,
then assembles the opponent's :class:`OpponentReveal` from the messages the
opponent delivered into OUR bounded inbox. If the opponent is unreachable or no
matching reveal arrives before a bounded number of polls, a
:class:`TechnicalFailure` is returned rather than hanging.

Validated against a live second peer (the independently-built Thief repo) in
session recovery step C, Task 5, and repeatedly since across real
six-sub-game bilateral series -- see `session_recovery_step_c/one_subgame/`
(development-workspace evidence, not included in this standalone package).
"""

from __future__ import annotations

import asyncio

from police_peer.infrastructure.inbox import PeerInbox
from police_peer.infrastructure.mcp_client import PeerUnavailableError, call_receive_turn
from police_peer.infrastructure.outbound_pacer import OutboundPacer
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
        opponent_token: str | None = None,
        pacer: OutboundPacer | None = None,
    ) -> None:
        self._url = opponent_url
        self._inbox = inbox
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._grid_size = grid_size
        self._opponent_token = opponent_token
        self._pacer = pacer

    async def _call_receive_turn(self, message: dict) -> dict:
        """Proactively paced (Gate A1 correction) when a pacer is given --
        never for local/no-token opponents, which stay byte-for-byte
        unaffected."""
        if self._pacer is None:
            return await call_receive_turn(self._url, message, token=self._opponent_token)
        async with self._pacer.slot():
            return await call_receive_turn(self._url, message, token=self._opponent_token)

    async def exchange_turn(
        self, commitment: dict, reveal: dict
    ) -> OpponentReveal | TechnicalFailure:
        """Deliver our messages, then await the opponent's public reveal.

        A rejected ack (``ok: False`` -- malformed, wrong sequence, wrong
        game_uid, ...) is a real protocol fault, not silently ignored: it
        becomes an explicit ``TechnicalFailure`` immediately rather than
        polling forever for a reveal the opponent never actually accepted
        our commitment/reveal well enough to answer. Every ``TechnicalFailure``
        below carries the REAL per-substep progress made before it, for the
        GUI protocol-status panel -- ``*_sent`` only turns True once a
        response (accepted or rejected) actually came back; a pure
        connection failure means we never confirmed anything left our side.
        """
        commit_sent = commit_acked = reveal_sent = False
        try:
            commit_ack = await self._call_receive_turn(commitment)
        except PeerUnavailableError as exc:
            return TechnicalFailure(f"opponent unreachable: {exc}")
        commit_sent = True
        if not commit_ack.get("ok"):
            return TechnicalFailure(f"opponent rejected our commitment: {commit_ack}", commit_sent)
        commit_acked = True
        try:
            reveal_ack = await self._call_receive_turn(reveal)
        except PeerUnavailableError as exc:
            return TechnicalFailure(f"opponent unreachable: {exc}", commit_sent, commit_acked)
        reveal_sent = True
        if not reveal_ack.get("ok"):
            return TechnicalFailure(
                f"opponent rejected our reveal: {reveal_ack}",
                commit_sent,
                commit_acked,
                reveal_sent,
            )
        return await self._await_opponent_reveal(commit_sent, commit_acked, reveal_sent)

    async def _await_opponent_reveal(
        self, commit_sent: bool, commit_acked: bool, reveal_sent: bool
    ) -> OpponentReveal | TechnicalFailure:
        for _ in range(self._max_polls):
            message = self._pop_reveal()
            if message is not None:
                return self._to_reveal(message)
            await asyncio.sleep(self._poll_interval)
        return TechnicalFailure(
            "no opponent reveal received within poll budget",
            commit_sent,
            commit_acked,
            reveal_sent,
        )

    def _pop_reveal(self) -> dict | None:
        for index, message in enumerate(self._inbox.turn_messages):
            if message.get("message_type") == "reveal":
                del self._inbox.turn_messages[index]
                self._prune_consumed_commitment(message)
                return message
        return None

    def _prune_consumed_commitment(self, reveal_message: dict) -> None:
        """A ``commitment`` is only needed until its matching ``reveal`` has
        been consumed (its role was to bind the sequence check at receive
        time); nothing ever pops it on its own, so across a multi-sub-game
        series it would otherwise accumulate without bound and eventually
        exhaust the bounded inbox's capacity (a real defect surfaced by
        session recovery step C, Task 7's real six-sub-game series -- see
        risk_register.md)."""
        env = reveal_message.get("envelope", {})
        for index, message in enumerate(self._inbox.turn_messages):
            other = message.get("envelope", {})
            if (
                message.get("message_type") == "commitment"
                and other.get("sub_game_number") == env.get("sub_game_number")
                and other.get("step") == env.get("step")
                and other.get("sender") == env.get("sender")
            ):
                del self._inbox.turn_messages[index]
                return

    def _to_reveal(self, message: dict) -> OpponentReveal:
        body = message.get("reveal", {})
        barrier = body.get("barrier_placed")
        return OpponentReveal(
            move=body.get("move"),
            hint=body.get("hint", ""),
            scent_grid=self._scent_grid_from_body(body),
            barrier=tuple(barrier) if barrier else None,
            claim_response=body.get("claim_response"),
            win_claim=bool(body.get("win_claim", False)),
        )

    def _scent_grid_from_body(self, body: dict) -> object:
        """The opponent's real scent grid, sealed and revealed as a field of
        their own reveal record (Batch 3.5 Task 4 -- previously this method
        scanned for a standalone ``"scent"`` message type that no sender ever
        produced, so it always fell back to an all-zero grid regardless of
        the opponent's real emission; see `observation_pipeline_audit.md`
        defect B1, development-workspace evidence, not included in this
        standalone package). Returns ``None`` (explicit missing evidence) or whatever
        raw structure was received, unvalidated -- validation happens
        downstream in ``ingest_opponent_reveal`` so malformed data is
        rejected rather than silently coerced into a false-valid zero grid."""
        return body.get("scent_grid")

"""Typed lifecycle events that drive state transitions.

An event is a pure value: a :class:`EventKind` plus an optional read-only
payload used by transition guards. Applying the same event twice, or an event
out of order, is a deterministic function of ``(state, event)`` -- there is no
hidden mutable input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class EventKind(StrEnum):
    """The set of things that can happen to the peer, each a transition trigger."""

    SERVER_STARTED = "server_started"
    BEGIN_NEGOTIATION = "begin_negotiation"
    SIGN_TERMS = "sign_terms"
    START_SUB_GAME = "start_sub_game"
    BEGIN_THINKING = "begin_thinking"
    COMMIT = "commit"
    COMMIT_SENT = "commit_sent"
    ACK_RECEIVED = "ack_received"
    REVEAL_SENT = "reveal_sent"
    TURN_VERIFIED = "turn_verified"
    SUB_GAME_ENDED = "sub_game_ended"
    BEGIN_AUDIT = "begin_audit"
    NEXT_SUB_GAME = "next_sub_game"
    COMPLETE_SERIES = "complete_series"
    QUIT = "quit"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class TransitionEvent:
    """A single lifecycle event and its (read-only) guard payload."""

    kind: EventKind
    payload: MappingProxyType[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def of(cls, kind: EventKind, **payload: Any) -> TransitionEvent:
        """Build an event with keyword payload, kept immutable for determinism."""
        return cls(kind=kind, payload=MappingProxyType(dict(payload)))

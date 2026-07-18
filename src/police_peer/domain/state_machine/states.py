"""The explicit lifecycle states of this peer.

The names are fixed by the Batch 2 specification and must not be renamed.
``TERMINAL_STATES`` are absorbing: no event moves the peer out of them, so a
restart requires a fresh process (see ``machine.py`` for the documented
restart/recovery decision).
"""

from __future__ import annotations

from enum import StrEnum


class PeerState(StrEnum):
    """One position in this peer's whole-of-life state machine."""

    INITIALIZING = "initializing"
    SERVER_READY = "server_ready"
    NEGOTIATING = "negotiating"
    SIGNED = "signed"
    WAITING = "waiting"
    THINKING = "thinking"
    COMMITTING = "committing"
    WAITING_FOR_ACK = "waiting_for_ack"
    REVEALING = "revealing"
    VERIFYING = "verifying"
    SUB_GAME_OVER = "sub_game_over"
    AUDITING = "auditing"
    SERIES_COMPLETE = "series_complete"
    ERROR = "error"
    QUIT = "quit"


#: Absorbing states -- once entered, no further transition is legal.
TERMINAL_STATES: frozenset[PeerState] = frozenset(
    {PeerState.SERIES_COMPLETE, PeerState.ERROR, PeerState.QUIT}
)

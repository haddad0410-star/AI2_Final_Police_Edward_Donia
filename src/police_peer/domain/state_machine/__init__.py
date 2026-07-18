"""Explicit peer lifecycle state machine (Batch 2, Phase 2).

Public surface: the states, events, the pure ``resolve`` transition function,
and the logged :class:`PeerStateMachine`.
"""

from __future__ import annotations

from police_peer.domain.state_machine.events import EventKind, TransitionEvent
from police_peer.domain.state_machine.machine import (
    IllegalTransitionError,
    PeerStateMachine,
    TransitionRecord,
)
from police_peer.domain.state_machine.states import TERMINAL_STATES, PeerState
from police_peer.domain.state_machine.transitions import resolve

__all__ = [
    "TERMINAL_STATES",
    "EventKind",
    "IllegalTransitionError",
    "PeerState",
    "PeerStateMachine",
    "TransitionEvent",
    "TransitionRecord",
    "resolve",
]

"""The transition table, guards, and the pure ``resolve`` function.

``resolve(state, event)`` is a pure function of its two inputs: it returns the
next :class:`PeerState` for a legal transition, or ``None`` for an illegal one.
No global or mutable state is consulted, so identical inputs always yield an
identical result (determinism requirement).
"""

from __future__ import annotations

from collections.abc import Callable

from police_peer.domain.state_machine.events import EventKind, TransitionEvent
from police_peer.domain.state_machine.states import TERMINAL_STATES, PeerState

_S = PeerState
_E = EventKind

#: The explicit ``(from_state, event) -> to_state`` transition table. Any
#: (state, event) pair absent from this table (and not a universal transition
#: below) is an illegal transition.
_TABLE: dict[tuple[PeerState, EventKind], PeerState] = {
    (_S.INITIALIZING, _E.SERVER_STARTED): _S.SERVER_READY,
    (_S.SERVER_READY, _E.BEGIN_NEGOTIATION): _S.NEGOTIATING,
    (_S.NEGOTIATING, _E.SIGN_TERMS): _S.SIGNED,
    (_S.SIGNED, _E.START_SUB_GAME): _S.WAITING,
    (_S.WAITING, _E.BEGIN_THINKING): _S.THINKING,
    (_S.THINKING, _E.COMMIT): _S.COMMITTING,
    (_S.COMMITTING, _E.COMMIT_SENT): _S.WAITING_FOR_ACK,
    (_S.WAITING_FOR_ACK, _E.ACK_RECEIVED): _S.REVEALING,
    (_S.REVEALING, _E.REVEAL_SENT): _S.VERIFYING,
    (_S.VERIFYING, _E.TURN_VERIFIED): _S.WAITING,
    (_S.VERIFYING, _E.SUB_GAME_ENDED): _S.SUB_GAME_OVER,
    # Survival: the sub-game reaches its move limit while WAITING for the next turn.
    (_S.WAITING, _E.SUB_GAME_ENDED): _S.SUB_GAME_OVER,
    (_S.SUB_GAME_OVER, _E.BEGIN_AUDIT): _S.AUDITING,
    (_S.AUDITING, _E.NEXT_SUB_GAME): _S.WAITING,
    (_S.AUDITING, _E.COMPLETE_SERIES): _S.SERIES_COMPLETE,
}

#: Guards keyed by the same ``(state, event)`` key: a transition present in the
#: table is only taken if its guard (if any) accepts the event payload. Guards
#: are pure predicates over the event payload -- never over external state.
_GUARDS: dict[tuple[PeerState, EventKind], Callable[[TransitionEvent], bool]] = {
    (_S.AUDITING, _E.NEXT_SUB_GAME): lambda e: bool(e.payload.get("more_sub_games")),
    (_S.AUDITING, _E.COMPLETE_SERIES): lambda e: not e.payload.get("more_sub_games", False),
}


def resolve(state: PeerState, event: TransitionEvent) -> PeerState | None:
    """Return the next state for a legal transition, or ``None`` if illegal.

    Universal transitions apply from any non-terminal state: ``FAIL`` routes to
    ``ERROR`` (runtime failure / technical loss) and ``QUIT`` routes to
    ``QUIT`` (clean shutdown). Terminal states accept no event at all.
    """
    if state in TERMINAL_STATES:
        return None
    if event.kind is _E.FAIL:
        return _S.ERROR
    if event.kind is _E.QUIT:
        return _S.QUIT
    key = (state, event.kind)
    target = _TABLE.get(key)
    if target is None:
        return None
    guard = _GUARDS.get(key)
    if guard is not None and not guard(event):
        return None
    return target

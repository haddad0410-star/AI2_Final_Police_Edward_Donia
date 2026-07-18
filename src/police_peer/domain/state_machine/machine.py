"""The peer state machine: applies events, logs every attempt, rejects illegal
transitions.

Restart / recovery decision (documented here and in docs/ARCHITECTURE.md):
``ERROR``, ``QUIT`` and ``SERIES_COMPLETE`` are TERMINAL. The machine never
re-enters ``INITIALIZING`` and offers no in-process restart -- recovery from a
technical loss or a crash is a fresh process, deliberately, so a corrupted
lifecycle can never be silently "healed" into continuing a cryptographically
sealed game. Runtime errors are surfaced by feeding a ``FAIL`` event, which is
a legal transition to ``ERROR`` from every non-terminal state.

Lifecycle changes MUST go through :meth:`PeerStateMachine.apply`; nothing else
may assign to ``state``. Strategy code is never given a reference to this class.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.state_machine.events import EventKind, TransitionEvent
from police_peer.domain.state_machine.states import PeerState
from police_peer.domain.state_machine.transitions import resolve


class IllegalTransitionError(Exception):
    """Raised by :meth:`PeerStateMachine.require` for a rejected transition."""


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    """A structured, append-only log entry for one transition attempt."""

    index: int
    from_state: PeerState
    event_kind: EventKind
    to_state: PeerState | None
    accepted: bool
    reason: str


class PeerStateMachine:
    """A logged, guard-checked lifecycle machine starting in ``INITIALIZING``."""

    def __init__(self, initial: PeerState = PeerState.INITIALIZING) -> None:
        self._state = initial
        self._log: list[TransitionRecord] = []

    @property
    def state(self) -> PeerState:
        """The current lifecycle state (read-only; mutate only via :meth:`apply`)."""
        return self._state

    @property
    def log(self) -> tuple[TransitionRecord, ...]:
        """The immutable, append-only transition log (accepted AND rejected)."""
        return tuple(self._log)

    def apply(self, event: TransitionEvent) -> TransitionRecord:
        """Attempt ``event`` from the current state; log and return the record.

        A legal transition advances ``state`` and is logged as accepted; an
        illegal one leaves ``state`` unchanged and is logged as rejected. Never
        raises -- callers wanting an exception use :meth:`require`.
        """
        target = resolve(self._state, event)
        if target is None:
            record = TransitionRecord(
                index=len(self._log),
                from_state=self._state,
                event_kind=event.kind,
                to_state=None,
                accepted=False,
                reason=f"illegal transition: {event.kind} not allowed from {self._state}",
            )
            self._log.append(record)
            return record
        record = TransitionRecord(
            index=len(self._log),
            from_state=self._state,
            event_kind=event.kind,
            to_state=target,
            accepted=True,
            reason="accepted",
        )
        self._log.append(record)
        self._state = target
        return record

    def require(self, event: TransitionEvent) -> TransitionRecord:
        """Like :meth:`apply`, but raise :class:`IllegalTransitionError` on rejection."""
        record = self.apply(event)
        if not record.accepted:
            raise IllegalTransitionError(record.reason)
        return record

    def fail(self, reason: str = "runtime error") -> TransitionRecord:
        """Force the peer into ``ERROR`` via a ``FAIL`` event (technical loss)."""
        return self.apply(TransitionEvent.of(EventKind.FAIL, reason=reason))

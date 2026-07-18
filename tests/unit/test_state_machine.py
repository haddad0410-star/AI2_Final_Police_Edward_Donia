"""Phase 2: the explicit peer lifecycle state machine.

Covers every legal transition, representative illegal ones, the full turn
lifecycle, sub-game and series completion, the technical-loss (ERROR) path,
clean QUIT, and duplicate / out-of-order events.
"""

from __future__ import annotations

import pytest

from police_peer.domain.state_machine import (
    EventKind,
    IllegalTransitionError,
    PeerState,
    PeerStateMachine,
    TransitionEvent,
    resolve,
)
from police_peer.domain.state_machine.states import TERMINAL_STATES

E = EventKind
S = PeerState


def _ev(kind: EventKind, **payload) -> TransitionEvent:
    return TransitionEvent.of(kind, **payload)


def _drive_to_signed(m: PeerStateMachine) -> None:
    m.require(_ev(E.SERVER_STARTED))
    m.require(_ev(E.BEGIN_NEGOTIATION))
    m.require(_ev(E.SIGN_TERMS))


def test_starts_in_initializing() -> None:
    assert PeerStateMachine().state is S.INITIALIZING


def test_negotiation_to_signed_path() -> None:
    m = PeerStateMachine()
    _drive_to_signed(m)
    assert m.state is S.SIGNED
    assert all(r.accepted for r in m.log)
    assert [r.to_state for r in m.log] == [S.SERVER_READY, S.NEGOTIATING, S.SIGNED]


def test_full_turn_lifecycle() -> None:
    m = PeerStateMachine()
    _drive_to_signed(m)
    m.require(_ev(E.START_SUB_GAME))
    assert m.state is S.WAITING
    for kind, expected in [
        (E.BEGIN_THINKING, S.THINKING),
        (E.COMMIT, S.COMMITTING),
        (E.COMMIT_SENT, S.WAITING_FOR_ACK),
        (E.ACK_RECEIVED, S.REVEALING),
        (E.REVEAL_SENT, S.VERIFYING),
        (E.TURN_VERIFIED, S.WAITING),
    ]:
        m.require(_ev(kind))
        assert m.state is expected


def test_sub_game_completion_and_next_sub_game() -> None:
    m = PeerStateMachine()
    _drive_to_signed(m)
    m.require(_ev(E.START_SUB_GAME))
    for kind in (E.BEGIN_THINKING, E.COMMIT, E.COMMIT_SENT, E.ACK_RECEIVED, E.REVEAL_SENT):
        m.require(_ev(kind))
    m.require(_ev(E.SUB_GAME_ENDED))
    assert m.state is S.SUB_GAME_OVER
    m.require(_ev(E.BEGIN_AUDIT))
    assert m.state is S.AUDITING
    m.require(_ev(E.NEXT_SUB_GAME, more_sub_games=True))
    assert m.state is S.WAITING


def test_series_completion() -> None:
    m = PeerStateMachine(initial=S.AUDITING)
    m.require(_ev(E.COMPLETE_SERIES, more_sub_games=False))
    assert m.state is S.SERIES_COMPLETE
    # Terminal: nothing further is accepted.
    assert m.apply(_ev(E.NEXT_SUB_GAME, more_sub_games=True)).accepted is False


def test_auditing_guard_blocks_wrong_branch() -> None:
    """The two AUDITING transitions are mutually exclusive on payload."""
    assert resolve(S.AUDITING, _ev(E.COMPLETE_SERIES, more_sub_games=True)) is None
    assert resolve(S.AUDITING, _ev(E.NEXT_SUB_GAME, more_sub_games=False)) is None
    assert resolve(S.AUDITING, _ev(E.COMPLETE_SERIES, more_sub_games=False)) is S.SERIES_COMPLETE
    assert resolve(S.AUDITING, _ev(E.NEXT_SUB_GAME, more_sub_games=True)) is S.WAITING


def test_technical_loss_path_to_error_from_any_state() -> None:
    for start in (S.WAITING, S.THINKING, S.REVEALING, S.NEGOTIATING):
        m = PeerStateMachine(initial=start)
        record = m.fail("boom")
        assert record.accepted is True
        assert m.state is S.ERROR


def test_error_is_terminal() -> None:
    m = PeerStateMachine(initial=S.ERROR)
    assert m.apply(_ev(E.SERVER_STARTED)).accepted is False
    assert m.state is S.ERROR


def test_clean_quit_from_non_terminal() -> None:
    m = PeerStateMachine(initial=S.WAITING)
    m.require(_ev(E.QUIT))
    assert m.state is S.QUIT
    assert m.state in TERMINAL_STATES


def test_quit_rejected_from_terminal() -> None:
    assert resolve(S.QUIT, _ev(E.QUIT)) is None


def test_illegal_transition_is_rejected_and_logged() -> None:
    m = PeerStateMachine()
    record = m.apply(_ev(E.COMMIT))  # not legal from INITIALIZING
    assert record.accepted is False
    assert record.to_state is None
    assert "illegal transition" in record.reason
    assert m.state is S.INITIALIZING
    assert m.log[-1] is record


def test_require_raises_on_illegal() -> None:
    m = PeerStateMachine()
    with pytest.raises(IllegalTransitionError):
        m.require(_ev(E.REVEAL_SENT))


def test_duplicate_event_second_is_rejected() -> None:
    m = PeerStateMachine()
    first = m.apply(_ev(E.SERVER_STARTED))
    second = m.apply(_ev(E.SERVER_STARTED))  # already left INITIALIZING
    assert first.accepted is True
    assert second.accepted is False
    assert m.state is S.SERVER_READY


def test_out_of_order_event_is_rejected() -> None:
    m = PeerStateMachine()
    m.require(_ev(E.SERVER_STARTED))
    # ACK_RECEIVED belongs much later in the lifecycle.
    assert m.apply(_ev(E.ACK_RECEIVED)).accepted is False
    assert m.state is S.SERVER_READY


def test_resolve_is_pure_and_deterministic() -> None:
    ev = _ev(E.BEGIN_THINKING)
    assert resolve(S.WAITING, ev) is resolve(S.WAITING, ev) is S.THINKING


def test_every_legal_table_transition_is_reachable() -> None:
    """Exercise each declared (state, event) mapping directly via resolve."""
    legal = {
        (S.INITIALIZING, E.SERVER_STARTED): S.SERVER_READY,
        (S.SERVER_READY, E.BEGIN_NEGOTIATION): S.NEGOTIATING,
        (S.NEGOTIATING, E.SIGN_TERMS): S.SIGNED,
        (S.SIGNED, E.START_SUB_GAME): S.WAITING,
        (S.WAITING, E.BEGIN_THINKING): S.THINKING,
        (S.THINKING, E.COMMIT): S.COMMITTING,
        (S.COMMITTING, E.COMMIT_SENT): S.WAITING_FOR_ACK,
        (S.WAITING_FOR_ACK, E.ACK_RECEIVED): S.REVEALING,
        (S.REVEALING, E.REVEAL_SENT): S.VERIFYING,
        (S.VERIFYING, E.TURN_VERIFIED): S.WAITING,
        (S.VERIFYING, E.SUB_GAME_ENDED): S.SUB_GAME_OVER,
        (S.SUB_GAME_OVER, E.BEGIN_AUDIT): S.AUDITING,
    }
    for (state, kind), expected in legal.items():
        assert resolve(state, _ev(kind)) is expected

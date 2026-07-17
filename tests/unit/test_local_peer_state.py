"""Tests that LocalPeerState (and the public envelope it exchanges) can only
ever hold this peer's own truth plus legally-public information -- never an
opponent_true_position field or equivalent backdoor."""

from __future__ import annotations

import dataclasses

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.captures import CaptureClaim
from police_peer.domain.hints import Hint, HintIntent
from police_peer.domain.observations import LocalObservation, PublicTurnEnvelope
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import ScentHistory, empty_scent_field
from police_peer.domain.state import LocalPeerState

FORBIDDEN_SUBSTRINGS = ("opponent_position", "opponent_true", "true_position", "enemy_position")


def _field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def test_local_peer_state_has_no_forbidden_field_names() -> None:
    names = _field_names(LocalPeerState)
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert not any(forbidden in name for name in names), names


def test_local_peer_state_only_position_field_is_its_own() -> None:
    """The only singular-Position field is `position` (this peer's own cell);
    `barriers_placed` is a tuple of PUBLIC barrier cells, not an opponent
    identity leak."""
    position_fields = {
        f.name for f in dataclasses.fields(LocalPeerState) if f.type in ("Position", Position)
    }
    assert position_fields == {"position"}


def test_public_turn_envelope_has_no_forbidden_field_names() -> None:
    names = _field_names(PublicTurnEnvelope)
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert not any(forbidden in name for name in names), names


def test_construct_local_peer_state() -> None:
    belief = uniform_prior(7)
    state = LocalPeerState(
        role=Role.POLICE,
        position=Position(0, 0),
        visited=frozenset({Position(0, 0)}),
        barriers_placed=(),
        barriers_remaining=14,
        step=0,
        sub_game_number=1,
        belief=belief,
        own_scent_field=empty_scent_field(7),
    )
    assert state.role is Role.POLICE
    assert state.opponent_scent_history == ScentHistory()

    advanced = state.with_step(1)
    assert advanced.step == 1
    assert state.step == 0  # original untouched -- immutable update


def test_construct_public_turn_envelope_and_observation() -> None:
    envelope = PublicTurnEnvelope(
        sender=Role.POLICE,
        step=3,
        sub_game_number=1,
        hint=Hint(text="near the old bridge", intent=HintIntent.TRUTH),
        scent=empty_scent_field(7),
        timestamp="2026-07-17T00:00:00+00:00",
        capture_claim=CaptureClaim(step=3, claimed_position=Position(2, 2)),
    )
    observation = LocalObservation(envelope=envelope, received_at_step=3)
    assert observation.envelope.sender is Role.POLICE
    assert observation.envelope.capture_claim.claimed_position == Position(2, 2)

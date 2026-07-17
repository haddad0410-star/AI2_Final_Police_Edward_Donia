"""Strict schema validation tests for every protocol message category."""

from __future__ import annotations

import pytest

from police_peer.domain.roles import Role
from police_peer.protocol.envelope import MessageEnvelope
from police_peer.protocol.messages_capture import (
    AuditSubmissionMessage,
    CaptureClaimMessage,
    CaptureResponseMessage,
)
from police_peer.protocol.messages_control import ControlMessage, ProtocolErrorMessage
from police_peer.protocol.messages_evidence import (
    BarrierDeclarationMessage,
    HintMessage,
    ScentPayloadMessage,
)
from police_peer.protocol.messages_handshake import (
    ConfigurationProposalMessage,
    HealthStatusMessage,
    NegotiationAcknowledgmentMessage,
    PeerDeclarationMessage,
)
from police_peer.protocol.messages_turn import (
    PublicTurnEnvelopeMessage,
    TurnCommitmentMessage,
    TurnRevealMessage,
)
from police_peer.shared.errors import SchemaValidationError


def envelope(**overrides) -> MessageEnvelope:
    defaults = {
        "schema_version": "1.0",
        "correlation_id": "corr-1",
        "game_id": "edward-donia-vs-opponent",
        "game_uid": "uid-123",
        "sub_game_number": 1,
        "step": 0,
        "sender": Role.POLICE,
        "timestamp": "2026-07-17T00:00:00+00:00",
        "sequence_id": 0,
    }
    defaults.update(overrides)
    return MessageEnvelope(**defaults)


def test_valid_envelope_constructs() -> None:
    envelope()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", ""),
        ("correlation_id", ""),
        ("game_id", ""),
        ("game_uid", ""),
        ("sub_game_number", 0),
        ("step", -1),
        ("timestamp", ""),
        ("sequence_id", -1),
    ],
)
def test_envelope_rejects_invalid_fields(field, value) -> None:
    with pytest.raises(SchemaValidationError):
        envelope(**{field: value})


def test_health_status_message() -> None:
    HealthStatusMessage(envelope=envelope(), status="ok")
    with pytest.raises(SchemaValidationError):
        HealthStatusMessage(envelope=envelope(), status="bogus")


def test_peer_declaration_message() -> None:
    PeerDeclarationMessage(
        envelope=envelope(),
        group_id="edward-donia",
        group_name="Edward-Donia",
        members=("Edward Haddad 214083115", "Donia Naser 212810493"),
        mcp_url="http://127.0.0.1:8901/mcp",
    )
    with pytest.raises(SchemaValidationError):
        PeerDeclarationMessage(
            envelope=envelope(), group_id="", group_name="x", members=(), mcp_url="http://x"
        )


def test_configuration_proposal_message() -> None:
    ConfigurationProposalMessage(
        envelope=envelope(), config_schema_version="1.0", config_sha256="a" * 64
    )
    with pytest.raises(SchemaValidationError):
        ConfigurationProposalMessage(
            envelope=envelope(), config_schema_version="1.0", config_sha256="too-short"
        )


def test_negotiation_acknowledgment_message() -> None:
    NegotiationAcknowledgmentMessage(envelope=envelope(), accepted=True, config_sha256_match=True)
    with pytest.raises(SchemaValidationError):
        NegotiationAcknowledgmentMessage(
            envelope=envelope(), accepted=False, config_sha256_match=False, reason=None
        )


def test_turn_commitment_message() -> None:
    TurnCommitmentMessage(envelope=envelope(), commit_hash="a" * 64)
    with pytest.raises(SchemaValidationError):
        TurnCommitmentMessage(envelope=envelope(), commit_hash="short")


def test_turn_reveal_message_requires_exactly_one_action() -> None:
    TurnRevealMessage(
        envelope=envelope(),
        move_direction="N",
        barrier_cell=None,
        hint_text="near the bridge",
        hint_intent="truth",
    )
    with pytest.raises(SchemaValidationError):
        TurnRevealMessage(
            envelope=envelope(),
            move_direction=None,
            barrier_cell=None,
            hint_text="x",
            hint_intent="truth",
        )
    with pytest.raises(SchemaValidationError):
        TurnRevealMessage(
            envelope=envelope(),
            move_direction="N",
            barrier_cell=(1, 1),
            hint_text="x",
            hint_intent="truth",
        )
    with pytest.raises(SchemaValidationError):
        TurnRevealMessage(
            envelope=envelope(),
            move_direction="N",
            barrier_cell=None,
            hint_text="x",
            hint_intent="maybe",
        )


def test_public_turn_envelope_message() -> None:
    PublicTurnEnvelopeMessage(
        envelope=envelope(),
        hint_text="hello",
        hint_intent="lie",
        scent_grid=((0.0,),),
    )
    with pytest.raises(SchemaValidationError):
        PublicTurnEnvelopeMessage(
            envelope=envelope(), hint_text="x", hint_intent="maybe", scent_grid=((0.0,),)
        )


def test_hint_message() -> None:
    HintMessage(envelope=envelope(), text="near the bridge", intent="truth")
    with pytest.raises(SchemaValidationError):
        HintMessage(envelope=envelope(), text="x", intent="maybe")


def test_scent_payload_message_shape_validation() -> None:
    ScentPayloadMessage(envelope=envelope(), grid_size=2, grid=((0.0, 0.0), (0.0, 0.0)))
    with pytest.raises(SchemaValidationError):
        ScentPayloadMessage(envelope=envelope(), grid_size=2, grid=((0.0,),))
    with pytest.raises(SchemaValidationError):
        ScentPayloadMessage(envelope=envelope(), grid_size=1, grid=((-1.0,),))


def test_barrier_declaration_message() -> None:
    BarrierDeclarationMessage(envelope=envelope(), cell_row=1, cell_col=1)
    with pytest.raises(SchemaValidationError):
        BarrierDeclarationMessage(envelope=envelope(), cell_row=-1, cell_col=1)


def test_capture_claim_and_response_messages() -> None:
    CaptureClaimMessage(envelope=envelope(), claimed_row=2, claimed_col=2)
    with pytest.raises(SchemaValidationError):
        CaptureClaimMessage(envelope=envelope(), claimed_row=-1, claimed_col=2)
    CaptureResponseMessage(envelope=envelope(), claimed_row=2, claimed_col=2, caught=True)


def test_audit_submission_message() -> None:
    AuditSubmissionMessage(envelope=envelope(), records=(), result_claim="capture")
    with pytest.raises(SchemaValidationError):
        AuditSubmissionMessage(envelope=envelope(), records=(), result_claim="bogus")


def test_control_message() -> None:
    ControlMessage(envelope=envelope(), kind="status", status_text="THINKING")
    with pytest.raises(SchemaValidationError):
        ControlMessage(envelope=envelope(), kind="bogus")


def test_protocol_error_message() -> None:
    ProtocolErrorMessage(envelope=envelope(), error_code="CONFIG_MISMATCH", message="oops")
    with pytest.raises(SchemaValidationError):
        ProtocolErrorMessage(envelope=envelope(), error_code="", message="oops")

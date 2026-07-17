"""MessageEnvelope: the common metadata every protocol message carries.

Compatible with integration_lab/audit/protocol_contract.md. Every message in
this package embeds one of these rather than repeating the fields, so
validation lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.roles import Role
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    """Metadata required on every wire message (where applicable)."""

    schema_version: str
    correlation_id: str
    game_id: str
    game_uid: str
    sub_game_number: int
    step: int
    sender: Role
    timestamp: str
    sequence_id: int

    def __post_init__(self) -> None:
        validate_envelope(self)


def validate_envelope(envelope: MessageEnvelope) -> None:
    if not envelope.schema_version:
        raise SchemaValidationError("schema_version must be non-empty")
    if not envelope.correlation_id:
        raise SchemaValidationError("correlation_id must be non-empty")
    if not envelope.game_id:
        raise SchemaValidationError("game_id must be non-empty")
    if not envelope.game_uid:
        raise SchemaValidationError("game_uid must be non-empty")
    if envelope.sub_game_number < 1:
        raise SchemaValidationError("sub_game_number must be >= 1")
    if envelope.step < 0:
        raise SchemaValidationError("step must be >= 0")
    if not isinstance(envelope.sender, Role):
        raise SchemaValidationError("sender must be a Role")
    if not envelope.timestamp:
        raise SchemaValidationError("timestamp must be non-empty")
    if envelope.sequence_id < 0:
        raise SchemaValidationError("sequence_id must be >= 0")

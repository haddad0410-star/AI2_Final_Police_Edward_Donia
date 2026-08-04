"""Handshake-phase messages: health/status, declaration, config proposal, ack.

These schemas are validated and the full negotiation lifecycle (actually
exchanging and acting on them over HTTP) is wired up by
infrastructure/mcp_server.py; the end-to-end commit/reveal/audit lifecycle
(see messages_turn.py, messages_capture.py) is likewise implemented and used
in real gameplay.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from police_peer.protocol.envelope import MessageEnvelope
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class HealthStatusMessage:
    """Response to a health/status check."""

    envelope: MessageEnvelope
    status: str  # "ok" | "starting" | "error"

    def __post_init__(self) -> None:
        if self.status not in ("ok", "starting", "error"):
            raise SchemaValidationError(f"invalid status: {self.status!r}")


@dataclass(frozen=True, slots=True)
class PeerDeclarationMessage:
    """This peer's identity, sent during negotiation."""

    envelope: MessageEnvelope
    group_id: str
    group_name: str
    members: tuple[str, ...]
    repos: dict[str, str] = field(default_factory=dict)
    mcp_url: str = ""

    def __post_init__(self) -> None:
        if not self.group_id:
            raise SchemaValidationError("group_id must be non-empty")
        if not self.group_name:
            raise SchemaValidationError("group_name must be non-empty")
        if not self.mcp_url:
            raise SchemaValidationError("mcp_url must be non-empty")


@dataclass(frozen=True, slots=True)
class ConfigurationProposalMessage:
    """The proposing peer's shared-config identity, for hash comparison."""

    envelope: MessageEnvelope
    config_schema_version: str
    config_sha256: str

    def __post_init__(self) -> None:
        if len(self.config_sha256) != 64:
            raise SchemaValidationError("config_sha256 must be a 64-char hex digest")
        if not self.config_schema_version:
            raise SchemaValidationError("config_schema_version must be non-empty")


@dataclass(frozen=True, slots=True)
class NegotiationAcknowledgmentMessage:
    """Reply to a ConfigurationProposalMessage: do our configs match?"""

    envelope: MessageEnvelope
    accepted: bool
    config_sha256_match: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.accepted and not self.reason:
            raise SchemaValidationError("reason is required when accepted=False")

"""Out-of-band control channel and structured protocol errors -- implemented
and wired to the `receive_control` server tool, not schema-only."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.protocol.envelope import MessageEnvelope
from police_peer.shared.errors import SchemaValidationError

VALID_CONTROL_KINDS = frozenset({"enable", "status", "restart", "quit"})


@dataclass(frozen=True, slots=True)
class ControlMessage:
    """Opt-in, out-of-band signal -- never part of the sealed game record."""

    envelope: MessageEnvelope
    kind: str
    status_text: str = ""

    def __post_init__(self) -> None:
        if self.kind not in VALID_CONTROL_KINDS:
            raise SchemaValidationError(f"invalid control kind: {self.kind!r}")


@dataclass(frozen=True, slots=True)
class ProtocolErrorMessage:
    """A structured error reply, so failures are machine-parseable, not free text."""

    envelope: MessageEnvelope
    error_code: str
    message: str

    def __post_init__(self) -> None:
        if not self.error_code:
            raise SchemaValidationError("error_code must be non-empty")
        if not self.message:
            raise SchemaValidationError("message must be non-empty")

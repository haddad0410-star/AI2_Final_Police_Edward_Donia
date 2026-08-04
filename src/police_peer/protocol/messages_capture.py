"""Capture-claim exchange and end-of-series audit submission -- implemented
and used in real gameplay, not schema-only."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.protocol.envelope import MessageEnvelope
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class CaptureClaimMessage:
    """Police claims the thief occupies (claimed_row, claimed_col)."""

    envelope: MessageEnvelope
    claimed_row: int
    claimed_col: int

    def __post_init__(self) -> None:
        if self.claimed_row < 0 or self.claimed_col < 0:
            raise SchemaValidationError("claimed_row/claimed_col must be >= 0")


@dataclass(frozen=True, slots=True)
class CaptureResponseMessage:
    """Thief's mandatory, honest reply to a CaptureClaimMessage."""

    envelope: MessageEnvelope
    claimed_row: int
    claimed_col: int
    caught: bool


@dataclass(frozen=True, slots=True)
class AuditSubmissionMessage:
    """End-of-series reveal: sealed records + nonces, recomputed and
    verified by the full commit-reveal audit lifecycle (implemented; see
    `domain/crypto/audit.py`)."""

    envelope: MessageEnvelope
    records: tuple[dict, ...]
    result_claim: str

    def __post_init__(self) -> None:
        if self.result_claim not in ("capture", "survival", "timeout"):
            raise SchemaValidationError(f"invalid result_claim: {self.result_claim!r}")

"""SealedTurnSession: enforces the Commit -> Acknowledge -> Reveal -> Audit
order for a single step (protocol_contract.md section 3.3).

The session withholds the nonce until :meth:`audit_reveal` and refuses to reveal
before an acknowledgment has been recorded, so a reveal-before-ack is a typed
error rather than a silent protocol break.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from police_peer.domain.crypto.audit import SealedRecord
from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.domain.crypto.sealing import compute_commit_hash


class SealError(Exception):
    """Raised when the commit/reveal sequence is used out of order."""


class SealPhase(IntEnum):
    """Monotonic phases; a session may only advance forwards."""

    CREATED = 0
    COMMITTED = 1
    ACKNOWLEDGED = 2
    REVEALED = 3
    AUDITED = 4


class SealedTurnSession:
    """A one-step commit/reveal state guard over a :class:`SealedTurnPayload`."""

    def __init__(self, payload: SealedTurnPayload) -> None:
        self._payload = payload
        self._hash = compute_commit_hash(payload)
        self._phase = SealPhase.CREATED

    @property
    def phase(self) -> SealPhase:
        return self._phase

    def commit(self) -> str:
        """Step 1: expose ``H_commit`` only (never the fields or nonce)."""
        if self._phase is not SealPhase.CREATED:
            raise SealError("commit may only be called once, first")
        self._phase = SealPhase.COMMITTED
        return self._hash

    def acknowledge(self) -> None:
        """Step 2: record the opponent's receipt of our commitment."""
        if self._phase is not SealPhase.COMMITTED:
            raise SealError("acknowledge requires a prior commit")
        self._phase = SealPhase.ACKNOWLEDGED

    def reveal(self) -> dict[str, Any]:
        """Step 3: reveal move + hint in the clear; the nonce stays hidden."""
        if self._phase is not SealPhase.ACKNOWLEDGED:
            raise SealError("reveal-before-acknowledgment is rejected")
        self._phase = SealPhase.REVEALED
        return self._payload.public_reveal_dict()

    def audit_reveal(self) -> SealedRecord:
        """Step 4: reveal the full payload (incl. nonce) for the final audit."""
        if self._phase is not SealPhase.REVEALED:
            raise SealError("audit_reveal requires a prior reveal")
        self._phase = SealPhase.AUDITED
        return SealedRecord(payload=self._payload, commit_hash=self._hash)

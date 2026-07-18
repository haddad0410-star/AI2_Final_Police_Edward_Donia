"""Final mutual audit: recompute every commitment and detect any tamper.

A single mismatch anywhere -- an altered field, a reused nonce, a missing
reveal, or a duplicated step -- is a hard ``tamper_forfeit`` (a technical loss,
no partial credit, no human judgement), per protocol_contract.md section 3.3.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.domain.crypto.sealing import verify_commit


class AuditVerdict(StrEnum):
    """The result category of a completed audit."""

    VERIFIED = "verified"
    TAMPER_FORFEIT = "tamper_forfeit"


@dataclass(frozen=True, slots=True)
class SealedRecord:
    """A revealed payload paired with the hash originally committed for it."""

    payload: SealedTurnPayload
    commit_hash: str


@dataclass(frozen=True, slots=True)
class AuditResult:
    """The outcome of :func:`audit_records`."""

    verdict: AuditVerdict
    reason: str
    offending_role: str | None = None
    offending_step: int | None = None

    @property
    def ok(self) -> bool:
        return self.verdict is AuditVerdict.VERIFIED


def _forfeit(reason: str, record: SealedRecord) -> AuditResult:
    return AuditResult(
        AuditVerdict.TAMPER_FORFEIT,
        reason,
        offending_role=record.payload.role,
        offending_step=record.payload.step,
    )


def _check_sequence_contiguous(materialized: list[SealedRecord]) -> AuditResult | None:
    """Reject a dropped or gapped step within any ``(sub_game, role)`` group.

    The sealed ``step`` field self-identifies each record's position, so a mere
    reordering of a complete set is not a tamper; a MISSING record, however,
    leaves a gap and is caught here (a duplicate is caught earlier). This is why
    no hash-chain is needed on the wire -- see docs/adr/ADR-0013.
    """
    groups: dict[tuple[int, str], list[SealedRecord]] = {}
    for record in materialized:
        groups.setdefault((record.payload.sub_game_number, record.payload.role), []).append(record)
    for records in groups.values():
        steps = sorted(r.payload.step for r in records)
        if steps != list(range(steps[0], steps[0] + len(steps))):
            return _forfeit("sequence gap: a step record is missing/reordered out", records[0])
    return None


def audit_records(records: Iterable[SealedRecord]) -> AuditResult:
    """Recompute and cross-check every sealed record; verify or forfeit.

    Detects, in order: an incomplete reveal (missing nonce), a duplicated
    ``(sub_game, step, role)`` reveal, a reused nonce, any commitment-hash
    mismatch from an altered sealed field, and a missing/gapped step in the
    per-group sequence.
    """
    materialized = list(records)
    seen_keys: set[tuple[int, int, str]] = set()
    seen_nonces: set[str] = set()
    for record in materialized:
        payload = record.payload
        if not payload.nonce:
            return _forfeit("incomplete reveal: missing nonce", record)
        key = (payload.sub_game_number, payload.step, payload.role)
        if key in seen_keys:
            return _forfeit(f"duplicate reveal for {key}", record)
        if payload.nonce in seen_nonces:
            return _forfeit("nonce reuse across steps", record)
        if not verify_commit(payload, record.commit_hash):
            return _forfeit("commitment hash mismatch (tamper)", record)
        seen_keys.add(key)
        seen_nonces.add(payload.nonce)
    if materialized:
        gap = _check_sequence_contiguous(materialized)
        if gap is not None:
            return gap
    return AuditResult(AuditVerdict.VERIFIED, "all commitments recomputed and matched")

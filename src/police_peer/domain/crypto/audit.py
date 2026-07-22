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
    """Reject a dropped, gapped, or reordered step within any ``(sub_game,
    role)`` group.

    Batch 4B Task 6: the sealed ``step`` field self-identifies each
    record's logical position, but the log's LIST order must still match
    it -- a reveal presented out of chronological order is a real protocol
    violation (Thief's independently-built ``steps_in_order`` check
    already caught this; this repo's own check had been limited to gap
    detection on the sorted step set, silently tolerating reordering,
    until the bilateral tamper matrix exposed the asymmetry and this fix
    closed it). A MISSING record leaves a gap and is caught here too (a
    duplicate is caught earlier). This is why no hash-chain is needed on
    the wire -- see docs/adr/ADR-0013.
    """
    groups: dict[tuple[int, str], list[SealedRecord]] = {}
    for record in materialized:
        groups.setdefault((record.payload.sub_game_number, record.payload.role), []).append(record)
    for records in groups.values():
        observed = [r.payload.step for r in records]
        steps = sorted(observed)
        if steps != list(range(steps[0], steps[0] + len(steps))):
            return _forfeit("sequence gap: a step record is missing/reordered out", records[0])
        if observed != steps:
            return _forfeit("reveal order does not match step order", records[0])
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

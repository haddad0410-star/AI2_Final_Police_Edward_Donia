"""Batch 4B Task 3/4/9: bilateral commitment verification -- the shared
service both the graphical/headless replay viewer (``gui.replay_view_model``)
and the Gmail report gate (``sdk.report_runner``) depend on, so neither the
GUI layer nor the report layer duplicates this logic (architecture rule:
CLI/GUI call into services, not the other way around).

Reuses the REAL, existing, unmodified replay-verification engine
(``services.replay_verifier.verify_replay``) for BOTH sides when both
sides' records use the current ``commitment/1`` canonical schema (Batch 4B
Task 3 unified the sealed field set so this repo's own crypto module can
correctly recompute the opponent's commitments too -- see
``integration_lab/evidence/batch4b/commitment_schema_audit.md``). Never
imports ``thief_peer``; only calls this repo's own verifier on whichever
directory it's given.

Legacy note (Rule 10): a genuinely cross-repo LEGACY (pre-Batch-4B) record
still cannot be cryptographically re-verified by the other side -- this is
an explicit, honestly-labeled limitation, never silently hidden, and never
applied to current ``commitment/1`` records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from police_peer.domain.crypto.payload import SCHEMA_VERSION
from police_peer.services.replay_verifier import ReplayReport, verify_replay

LEGACY_VERDICT = "NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE_LEGACY_SCHEMA"


@dataclass(frozen=True, slots=True)
class SideVerification:
    directory: str
    verdict: str
    ok: bool
    findings: tuple[str, ...]
    independently_verified: bool
    schema_version: str | None


def peek_schema_version(directory: Path) -> str | None:
    """Read just enough to know which schema this side's records use,
    without attempting a (possibly-crashing, for a legacy opponent record)
    full reconstruction first."""
    logs = sorted(directory.glob("log_*.json"))
    if not logs:
        return None
    try:
        data = json.loads(logs[0].read_text())
    except (OSError, ValueError):
        return None
    steps = data.get("steps") or []
    return steps[0].get("schema_version") if steps else None


def verify_side(directory: Path) -> SideVerification:
    """Fully, independently verify ANY directory (own or opponent) whose
    records use the current ``commitment/1`` schema -- the real verifier
    is schema-agnostic once the field set is unified, so no role-specific
    code path is needed here. A LEGACY-schema record (pre-Batch 4B) falls
    back to an explicit not-independently-verified label -- never silently
    claimed as verified."""
    schema = peek_schema_version(directory)
    if schema is not None and schema != SCHEMA_VERSION:
        return SideVerification(
            directory=str(directory),
            verdict=LEGACY_VERDICT,
            ok=True,
            findings=(),
            independently_verified=False,
            schema_version=schema,
        )
    report: ReplayReport = verify_replay(directory)
    return SideVerification(
        directory=str(directory),
        verdict=report.verdict,
        ok=report.ok,
        findings=tuple(report.findings),
        independently_verified=True,
        schema_version=schema,
    )


def verify_bilateral(
    police_dir: Path, thief_dir: Path
) -> tuple[SideVerification, SideVerification, bool]:
    """Independently verify BOTH sides; ``full_bilateral_verification`` is
    true only when both were independently verified AND both report
    VERIFIED."""
    police_side = verify_side(police_dir)
    thief_side = verify_side(thief_dir)
    full_bilateral = (
        police_side.independently_verified
        and police_side.ok
        and thief_side.independently_verified
        and thief_side.ok
    )
    return police_side, thief_side, full_bilateral

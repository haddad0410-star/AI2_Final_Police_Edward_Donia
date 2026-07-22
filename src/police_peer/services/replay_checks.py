"""Per-log and per-score integrity checks for the replay verifier (Phase 12).

Reconstructs each sealed record from a log's step dicts and re-runs the Phase 4
audit (which recomputes every commitment via ``secrets.compare_digest``, plus
nonce/duplicate/sequence checks). Also recomputes each declared score from the
declared result via the config's scoring table.
"""

from __future__ import annotations

from typing import Any

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import SealedRecord, SealedTurnPayload, audit_records
from police_peer.domain.crypto.payload import CANONICAL_FIELD_SET, SCHEMA_VERSION
from police_peer.domain.scoring import score_sub_game
from police_peer.shared.config_sections import Scoring

#: Bookkeeping keys allowed alongside the canonical commitment fields in a
#: log-artifact step (added by the log writer, never part of H_commit).
_LOG_STEP_EXTRA_KEYS = frozenset({"commit_hash"})


def payload_from_step(step: dict) -> SealedTurnPayload:
    """Rebuild a :class:`SealedTurnPayload` from one revealed log step.

    Handles both the current ``commitment/1`` shape (a top-level
    ``position``/``config_sha256``, bilaterally verifiable -- see
    ``integration_lab/evidence/batch4b/commitment_schema_audit.md``) and
    the legacy ``commit-reveal/2`` shape (Batch 1-4A evidence, where
    ``config_sha256`` was nested inside ``state``) so old evidence remains
    self-verifiable under its own original schema. A record is only ever
    reconstructed using the schema it declares; the two shapes are never
    mixed.
    """
    barrier = step.get("barrier_placed")
    claim = step.get("capture_claim")
    schema_version = step.get("schema_version", "commit-reveal/1")
    if "position" in step:
        position = tuple(step["position"])
        config_sha256 = step["config_sha256"]
    else:  # legacy commit-reveal/1 or /2: position + config_sha256 nested in `state`
        legacy_state = step.get("state") or {}
        position = tuple(legacy_state.get("position", (0, 0)))
        config_sha256 = legacy_state.get("config_sha256", "")
    return SealedTurnPayload(
        step=step["step"],
        role=step["role"],
        sub_game_number=step["sub_game_number"],
        position=position,
        move=step["move"],
        barrier_placed=tuple(barrier) if barrier else None,
        intent=step["intent"],
        hint=step["hint"],
        scent_digest=step["scent_digest"],
        scent_grid=tuple(tuple(row) for row in step["scent_grid"]) if "scent_grid" in step else (),
        capture_claim=tuple(claim) if claim else None,
        claim_response=step["claim_response"],
        win_claim=step["win_claim"],
        config_sha256=config_sha256,
        timestamp=step["timestamp"],
        nonce=step["nonce"],
        schema_version=schema_version,
    )


def _check_role_fields(step: dict, number, findings: list[str]) -> None:
    """Batch 4B Task 6: a role-specific field placed on the wrong role is a
    real tamper, not a stylistic issue -- Police must never carry a
    Thief-only ``claim_response``/``win_claim`` value, and Thief must
    never carry a Police-only ``barrier_placed``/``capture_claim`` value."""
    role, step_no = step.get("role"), step.get("step")
    if role == "police":
        if step.get("claim_response") is not None:
            findings.append(
                f"sub-game {number} step {step_no}: police record has claim_response set"
            )
        if step.get("win_claim"):
            findings.append(f"sub-game {number} step {step_no}: police record has win_claim=true")
    elif role == "thief":
        if step.get("barrier_placed") is not None:
            findings.append(
                f"sub-game {number} step {step_no}: thief record has barrier_placed set"
            )
        if step.get("capture_claim") is not None:
            findings.append(f"sub-game {number} step {step_no}: thief record has capture_claim set")


def _check_unknown_fields(step: dict, number, findings: list[str]) -> None:
    """Batch 4B Task 3: reject unknown fields on a current-schema record --
    an extra key could otherwise silently alter what the receiver thinks
    was committed."""
    if step.get("schema_version") != SCHEMA_VERSION:
        return
    extra = set(step) - CANONICAL_FIELD_SET - _LOG_STEP_EXTRA_KEYS
    if extra:
        findings.append(
            f"sub-game {number} step {step.get('step')}: unknown field(s) {sorted(extra)}"
        )


def verify_log(log: dict, grid_size: int) -> list[str]:
    """Return findings for one log: commitment audit + barrier/capture bounds
    + role-field consistency + unknown-field rejection."""
    findings: list[str] = []
    number = log.get("sub_game_number", "?")
    records = [SealedRecord(payload_from_step(s), s["commit_hash"]) for s in log["steps"]]
    audit = audit_records(records)
    if not audit.ok:
        findings.append(f"sub-game {number}: {audit.reason} (step {audit.offending_step})")
    for step in log["steps"]:
        for name in ("barrier_placed", "capture_claim"):
            cell = step.get(name)
            if cell is not None and not (0 <= cell[0] < grid_size and 0 <= cell[1] < grid_size):
                findings.append(f"sub-game {number}: {name} {cell} out of bounds")
        _check_role_fields(step, number, findings)
        _check_unknown_fields(step, number, findings)
    return findings


def scoring_from_terms(terms: dict[str, Any]) -> Scoring:
    """Build a :class:`Scoring` from the config artifact's terms (ignores _notes)."""
    raw = {k: v for k, v in terms["scoring"].items() if not k.startswith("_")}
    return Scoring(**raw)


def verify_scores(result: dict, scoring: Scoring) -> list[str]:
    """Recompute each declared score from its result and check the totals."""
    findings: list[str] = []
    police_sum = 0
    thief_sum = 0
    for entry in result["sub_games"]:
        outcome = SubGameResult(entry["result"])
        expected = score_sub_game(outcome, scoring)
        declared = (entry["police_score"], entry["thief_score"])
        if declared != expected:
            findings.append(f"sub-game {entry['sub_game_number']}: score {declared} != {expected}")
        police_sum += entry["police_score"]
        thief_sum += entry["thief_score"]
    declared_totals = (result["police_total"], result["thief_total"])
    if result.get("agreement_status") != "disputed_zeroed" and (police_sum, thief_sum) != (
        declared_totals
    ):
        findings.append("declared totals do not match the sum of sub-game scores")
    return findings

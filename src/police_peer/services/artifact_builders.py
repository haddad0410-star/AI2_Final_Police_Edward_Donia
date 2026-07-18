"""Build the JSON artifact models from live runtime results (Batch 2, Phase 11)."""

from __future__ import annotations

from typing import Any

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import AuditResult, SealedRecord
from police_peer.services.artifact_models import ConfigArtifact, LogArtifact, ResultArtifact
from police_peer.services.series_runtime import SeriesResult

_WINNER = {SubGameResult.CAPTURE: "police", SubGameResult.SURVIVAL: "thief"}


def build_config_artifact(
    game_uid: str, game_id: str, sub_game_number: int, config_sha256: str, terms: dict
) -> ConfigArtifact:
    """Config artifact for one sub-game (agreed terms + hash)."""
    return ConfigArtifact(game_uid, game_id, sub_game_number, config_sha256, terms)


def build_log_artifact(
    game_uid: str,
    game_id: str,
    sub_game_number: int,
    records: tuple[SealedRecord, ...],
    audit: AuditResult,
) -> LogArtifact:
    """Log artifact: sealed step records (nonces revealed) + audit verdict."""
    steps: list[dict[str, Any]] = [
        {**record.payload.to_canonical_dict(), "commit_hash": record.commit_hash}
        for record in records
    ]
    return LogArtifact(
        game_uid=game_uid,
        game_id=game_id,
        sub_game_number=sub_game_number,
        steps=steps,
        audit_verdict=audit.verdict.value,
        audit_reason=audit.reason,
    )


def build_result_artifact(
    game_uid: str,
    game_id: str,
    git_commit: str,
    group_id: str,
    config_sha256: str,
    series: SeriesResult,
) -> ResultArtifact:
    """Whole-series result artifact with per-sub-game scores + final agreement."""
    sub_games = [
        {
            "sub_game_number": r.sub_game_number,
            "result": r.result.value,
            "winner": _WINNER.get(r.result),
            "police_score": r.police_score,
            "thief_score": r.thief_score,
            "steps": r.steps,
            "audit_ok": r.audit_ok,
        }
        for r in series.sub_games
    ]
    return ResultArtifact(
        game_uid=game_uid,
        game_id=game_id,
        git_commit=git_commit,
        group_id=group_id,
        config_sha256=config_sha256,
        sub_games=sub_games,
        police_total=series.agreement.police_total,
        thief_total=series.agreement.thief_total,
        agreement_status=series.agreement.status,
        agreed=series.agreement.agreed,
    )

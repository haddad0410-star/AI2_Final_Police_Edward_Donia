"""Assemble and save the four standardized JSON artifacts for a completed
series (Batch 2 Phase 11).

Reuses the already-implemented, already-tested model/save layer
(``artifact_models.py``, ``artifact_builders.py``, ``artifacts.py``) --
this module is purely the orchestration that was missing from the actual
``run-series`` execution path (found during the session-recovery-step-B
Phase 10-12 audit; see ``session_recovery_step_b/police_phase_10_12/``,
development-workspace evidence, not included in this standalone package):
the artifact writer existed and was unit-tested in
isolation, but nothing ever called it from ``game_runner.py``/the CLI, so a
real series run produced no artifact files on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.crypto import audit_records
from police_peer.domain.declaration_builder import DeclarationInputs, build_declaration
from police_peer.domain.repo_metadata import code_version, git_commit_hash
from police_peer.services.artifact_builders import (
    build_config_artifact,
    build_log_artifact,
    build_result_artifact,
)
from police_peer.services.artifacts import (
    config_filename,
    declaration_filename,
    log_filename,
    result_filename,
    save_artifact,
)
from police_peer.services.series_runtime import SeriesResult
from police_peer.shared.private_config import PrivateGameConfig

REPO_ROOT = Path(__file__).resolve().parents[3]


def write_series_artifacts(
    artifacts_dir: Path,
    config_dir: Path,
    private: PrivateGameConfig,
    game_id: str,
    game_uid: str,
    config_sha256: str,
    series: SeriesResult,
) -> list[Path]:
    """Write one declaration, one config+log per sub-game, and one result
    artifact for a completed series; return every path written."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    terms = json.loads((config_dir / "game.json").read_text(encoding="utf-8"))
    commit = git_commit_hash(REPO_ROOT)
    written: list[Path] = []

    league = terms.get("network_and_league", {})
    declaration = build_declaration(
        DeclarationInputs(
            role="police",
            game_id=game_id,
            game_uid=game_uid,
            group_id=private.game.group_id,
            group_name=private.game.group_name,
            members=private.game.members,
            police_repository=private.game.repos.get("police", "local-placeholder://police_peer"),
            thief_repository=private.game.repos.get("thief", "local-placeholder://thief_peer"),
            police_mcp_url=f"http://127.0.0.1:{private.network.my_port}/mcp",
            thief_mcp_url=private.network.opponent_url,
            token_budget=league.get("token_budget_per_series", 0),
            num_sub_games=league.get("num_games", len(series.sub_games)),
            shared_config_sha256=config_sha256,
            code_version=code_version(REPO_ROOT / "pyproject.toml"),
            git_commit=commit,
            strategy_class=private.strategy.police_class,
            banter_provider=private.trash_talk.provider,
        )
    )
    written.append(save_artifact(declaration, artifacts_dir / declaration_filename(game_id)))

    for record, records in zip(series.sub_games, series.records_by_sub_game, strict=True):
        n = record.sub_game_number
        config_artifact = build_config_artifact(game_uid, game_id, n, config_sha256, terms)
        written.append(save_artifact(config_artifact, artifacts_dir / config_filename(game_id, n)))

        audit = audit_records(records)
        log_artifact = build_log_artifact(game_uid, game_id, n, records, audit)
        written.append(save_artifact(log_artifact, artifacts_dir / log_filename(game_id, n)))

    result_artifact = build_result_artifact(
        game_uid, game_id, commit, private.game.group_id, config_sha256, series
    )
    written.append(save_artifact(result_artifact, artifacts_dir / result_filename(game_id)))
    return written

"""Batch 4A Task 12: report_runner refuses to build a report from artifacts
that fail the real replay verifier -- reuses the same fixture-writing
helpers as ``tests/security/test_replay_verifier.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import AuditResult, AuditVerdict, SealedRecord, compute_commit_hash
from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.sdk.report_runner import (
    ReportRefusedError,
    build_report_from_artifacts,
    run_dry_run,
)
from police_peer.services.artifact_builders import build_log_artifact, build_result_artifact
from police_peer.services.artifact_models import ConfigArtifact
from police_peer.services.artifacts import (
    config_filename,
    log_filename,
    result_filename,
    save_artifact,
)
from police_peer.services.series_runtime import SeriesResult
from police_peer.services.series_scoring import FinalAgreement, SubGameRecord
from police_peer.shared.canonical_json import canonical_json_bytes
from police_peer.shared.config_loader import sha256_hex

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"
UID = "abcabcab-1111-2222-3333-444444444444"
GID = "edward-donia"
N_GAMES = 1


def _payload(sub_game: int, step: int, *, role: str = "police") -> SealedTurnPayload:
    police_only = role == "police"
    return SealedTurnPayload(
        step=step,
        role=role,
        sub_game_number=sub_game,
        position=(step, 0),
        move="S" if police_only else "N",
        barrier_placed=None,
        intent="truth",
        hint="south looks fine" if police_only else "north looks fine",
        scent_digest="d" * 64,
        scent_grid=((0.0, 0.0), (0.0, 0.0)),
        capture_claim=(step, 0) if police_only else None,
        claim_response=None if police_only else True,
        win_claim=False,
        config_sha256=sha256_hex(CONFIG_DIR / "game.json"),
        timestamp="2026-07-18T00:00:00+00:00",
        nonce=f"{role}{sub_game:031x}{step:032x}",
    )


def _write_bundle(directory: Path, *, role: str = "police") -> None:
    with open(CONFIG_DIR / "game.json", encoding="utf-8") as handle:
        terms = json.load(handle)
    config_sha = sha256_hex(CONFIG_DIR / "game.json")
    for n in range(1, N_GAMES + 1):
        recs = tuple(
            SealedRecord(_payload(n, s, role=role), compute_commit_hash(_payload(n, s, role=role)))
            for s in range(2)
        )
        save_artifact(
            ConfigArtifact(UID, GID, n, config_sha, terms), directory / config_filename(GID, n)
        )
        log = build_log_artifact(UID, GID, n, recs, AuditResult(AuditVerdict.VERIFIED, "ok"))
        save_artifact(log, directory / log_filename(GID, n))
    sub_records = tuple(
        SubGameRecord(n, SubGameResult.CAPTURE, 20, 5, 2, True) for n in range(1, N_GAMES + 1)
    )
    series = SeriesResult(
        sub_records, FinalAgreement(True, "agreed", 20 * N_GAMES, 5 * N_GAMES), "completed", None
    )
    result = build_result_artifact(UID, GID, "deadbeef", GID, config_sha, series)
    save_artifact(result, directory / result_filename(GID))
    decl = {
        "schema_version": "declaration/1",
        "game_uid": UID,
        "game_id": GID,
        "role": role,
        "group_id": GID,
        "members": [],
        "hardware": {},
        "git_commit": "deadbeef",
        "banter_provider": "template",
    }
    (directory / f"declaration_{GID}.json").write_bytes(canonical_json_bytes(decl) + b"\n")


def test_valid_artifacts_produce_a_report(tmp_path) -> None:
    _write_bundle(tmp_path)
    report = build_report_from_artifacts(tmp_path)
    assert report["game_uid"] == UID


def test_dry_run_works_end_to_end(tmp_path) -> None:
    _write_bundle(tmp_path)
    result = run_dry_run(tmp_path)
    assert result["would_send_to"] == "rmisegal+uoh26finalgame@gmail.com"


def test_tampered_artifacts_are_refused(tmp_path) -> None:
    _write_bundle(tmp_path)
    log_path = tmp_path / log_filename(GID, 1)
    data = json.loads(log_path.read_text())
    data["steps"][0]["commit_hash"] = "0" * 64
    log_path.write_text(json.dumps(data))
    try:
        build_report_from_artifacts(tmp_path)
        raise AssertionError("expected ReportRefusedError")
    except ReportRefusedError as exc:
        assert "unverified" in str(exc) or "TAMPERED" in str(exc)


def test_missing_artifacts_are_refused(tmp_path) -> None:
    try:
        build_report_from_artifacts(tmp_path)
        raise AssertionError("expected ReportRefusedError")
    except ReportRefusedError:
        pass


def test_bilateral_gate_accepts_when_both_sides_verified(tmp_path) -> None:
    own_dir, opp_dir = tmp_path / "own", tmp_path / "opp"
    own_dir.mkdir()
    opp_dir.mkdir()
    _write_bundle(own_dir, role="police")
    _write_bundle(opp_dir, role="thief")
    result = run_dry_run(own_dir, opp_dir)
    assert result["would_send_to"] == "rmisegal+uoh26finalgame@gmail.com"


def test_bilateral_gate_refuses_when_own_side_tampered(tmp_path) -> None:
    own_dir, opp_dir = tmp_path / "own", tmp_path / "opp"
    own_dir.mkdir()
    opp_dir.mkdir()
    _write_bundle(own_dir, role="police")
    _write_bundle(opp_dir, role="thief")
    log_path = own_dir / log_filename(GID, 1)
    data = json.loads(log_path.read_text())
    data["steps"][0]["commit_hash"] = "0" * 64
    log_path.write_text(json.dumps(data))
    try:
        build_report_from_artifacts(own_dir, opp_dir)
        raise AssertionError("expected ReportRefusedError")
    except ReportRefusedError as exc:
        assert "bilateral" in str(exc)


def test_bilateral_gate_refuses_when_opponent_side_tampered(tmp_path) -> None:
    own_dir, opp_dir = tmp_path / "own", tmp_path / "opp"
    own_dir.mkdir()
    opp_dir.mkdir()
    _write_bundle(own_dir, role="police")
    _write_bundle(opp_dir, role="thief")
    log_path = opp_dir / log_filename(GID, 1)
    data = json.loads(log_path.read_text())
    data["steps"][0]["hint"] = "tampered"
    log_path.write_text(json.dumps(data))
    try:
        build_report_from_artifacts(own_dir, opp_dir)
        raise AssertionError("expected ReportRefusedError")
    except ReportRefusedError as exc:
        assert "bilateral" in str(exc)

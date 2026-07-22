"""Phase 11: standardized JSON artifacts -- filenames, round-trips, negatives."""

from __future__ import annotations

import pytest

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import (
    AuditResult,
    AuditVerdict,
    SealedRecord,
    SealedTurnPayload,
    compute_commit_hash,
)
from police_peer.services.artifact_builders import (
    build_config_artifact,
    build_log_artifact,
    build_result_artifact,
)
from police_peer.services.artifact_models import ConfigArtifact, LogArtifact, ResultArtifact
from police_peer.services.artifacts import (
    assert_consistent_game_uid,
    config_filename,
    declaration_filename,
    load_json,
    log_filename,
    result_filename,
    save_artifact,
)
from police_peer.services.series_runtime import SeriesResult
from police_peer.services.series_scoring import FinalAgreement, SubGameRecord
from police_peer.shared.errors import SchemaValidationError

UID = "11111111-2222-3333-4444-555555555555"
GID = "edward-donia"
SHA = "a" * 64


def _payload(step: int) -> SealedTurnPayload:
    return SealedTurnPayload(
        step=step,
        role="police",
        sub_game_number=1,
        position=(0, 0),
        move="N",
        barrier_placed=None,
        intent="truth",
        hint="north looks fine",
        scent_digest="d" * 64,
        scent_grid=((0.0, 0.0), (0.0, 0.0)),
        capture_claim=(0, 0),
        claim_response=None,
        win_claim=False,
        config_sha256=SHA,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce=f"{step:064x}",
    )


def _series() -> SeriesResult:
    records = (
        SubGameRecord(1, SubGameResult.CAPTURE, 20, 5, 3, True),
        SubGameRecord(2, SubGameResult.SURVIVAL, 5, 10, 35, True),
    )
    return SeriesResult(records, FinalAgreement(True, "agreed", 25, 15), "completed", None)


def test_filenames_derived_from_game_id() -> None:
    assert declaration_filename(GID) == "declaration_edward-donia.json"
    assert config_filename(GID, 3) == "config_edward-donia_g03.json"
    assert log_filename(GID, 12) == "log_edward-donia_g12.json"
    assert result_filename(GID) == "result_edward-donia.json"


def test_config_artifact_round_trip(tmp_path) -> None:
    art = build_config_artifact(UID, GID, 1, SHA, {"grid_size": 7})
    path = save_artifact(art, tmp_path / config_filename(GID, 1))
    reloaded = ConfigArtifact.from_dict(load_json(path))
    assert reloaded.game_uid == UID
    assert reloaded.terms["grid_size"] == 7


def test_log_artifact_round_trip(tmp_path) -> None:
    records = tuple(SealedRecord(_payload(s), compute_commit_hash(_payload(s))) for s in range(2))
    audit = AuditResult(AuditVerdict.VERIFIED, "ok")
    art = build_log_artifact(UID, GID, 1, records, audit)
    path = save_artifact(art, tmp_path / log_filename(GID, 1))
    reloaded = LogArtifact.from_dict(load_json(path))
    assert len(reloaded.steps) == 2
    assert reloaded.steps[0]["nonce"] == f"{0:064x}"  # nonce present post-reveal
    assert reloaded.audit_verdict == "verified"


def test_result_artifact_round_trip(tmp_path) -> None:
    art = build_result_artifact(UID, GID, "deadbeef", GID, SHA, _series())
    path = save_artifact(art, tmp_path / result_filename(GID))
    reloaded = ResultArtifact.from_dict(load_json(path))
    assert reloaded.police_total == 25
    assert reloaded.sub_games[0]["winner"] == "police"
    assert reloaded.sub_games[1]["winner"] == "thief"
    assert reloaded.agreed is True


def test_consistent_game_uid_across_four(tmp_path) -> None:
    config = build_config_artifact(UID, GID, 1, SHA, {}).to_dict()
    result = build_result_artifact(UID, GID, "abc", GID, SHA, _series()).to_dict()
    assert assert_consistent_game_uid(config, result) == UID


def test_mismatched_game_uid_rejected() -> None:
    a = {"game_uid": UID}
    b = {"game_uid": "other"}
    with pytest.raises(SchemaValidationError):
        assert_consistent_game_uid(a, b)


def test_malformed_artifact_rejected_on_load() -> None:
    with pytest.raises(SchemaValidationError):
        ConfigArtifact.from_dict({"game_uid": UID})  # missing fields


def test_missing_required_field_rejected() -> None:
    with pytest.raises(SchemaValidationError):
        ResultArtifact.from_dict({"game_uid": UID, "game_id": GID})


def test_bad_config_hash_rejected() -> None:
    with pytest.raises(SchemaValidationError):
        ConfigArtifact(UID, GID, 1, "tooshort", {}).validate()


def test_no_credentials_scan_blocks_secret(tmp_path) -> None:
    sneaky = build_config_artifact(UID, GID, 1, SHA, {"note": "api_key=SECRETVALUE"})
    with pytest.raises(SchemaValidationError):
        save_artifact(sneaky, tmp_path / "x.json")

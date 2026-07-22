"""Batch 4A Task 9: Gmail report-schema tests. Uses a synthetic declaration/
result/log fixture (matching the real field shapes produced by
``services/artifact_builders.py``), consistent with this project's existing
test convention (e.g. ``tests/security/test_replay_verifier.py``) of not
depending on files outside the repository.
"""

from __future__ import annotations

import hashlib
import json

from police_peer.domain.gmail_report_schema import MANDATORY_RECIPIENT, build_report

_DECLARATION = {
    "schema_version": "declaration/2",
    "game_id": "edward-donia",
    "game_uid": "abc-123",
    "group_id": "edward-donia",
    "members": ["Edward Haddad 214083115", "Donia Naser 212810493"],
    "police_repository": "https://github.com/example/police",
    "thief_repository": "https://github.com/example/thief",
    "police_mcp_url": "http://127.0.0.1:8901/mcp",
    "thief_mcp_url": "http://127.0.0.1:8902/mcp",
    "git_commit": "deadbeef" * 5,
    "hardware": {"cpu_model": "Apple M2", "ram_gb": 8.0},
    "strategy_class": "police_peer.strategy.belief_cutoff_police_brain:BeliefCutoffPoliceBrain",
    "banter_provider": "template",
}
_RESULT = {
    "game_id": "edward-donia",
    "game_uid": "abc-123",
    "config_sha256": "cafebabe" * 8,
    "police_total": 120,
    "thief_total": 30,
    "agreed": True,
    "agreement_status": "unverified_self_play",
    "sub_games": [
        {
            "sub_game_number": n,
            "result": "capture",
            "police_score": 20,
            "thief_score": 5,
            "audit_ok": True,
        }
        for n in range(1, 7)
    ],
}
_LOG = {
    "steps": [
        {"step": 0, "timestamp": "2026-07-22T08:05:59.000000+00:00"},
        {"step": 1, "timestamp": "2026-07-22T08:06:00.000000+00:00"},
    ]
}


def test_report_built_from_artifacts() -> None:
    report = build_report(declaration=_DECLARATION, result=_RESULT, artifact_paths=[], logs=[_LOG])
    assert report["recipient"] == MANDATORY_RECIPIENT
    assert report["game_id"] == _DECLARATION["game_id"]
    assert report["game_uid"] == _DECLARATION["game_uid"]
    assert report["scores"]["police_total"] == _RESULT["police_total"]
    assert len(report["sub_game_outcomes"]) == 6


def test_report_never_includes_credentials_or_secrets() -> None:
    report = build_report(declaration=_DECLARATION, result=_RESULT, artifact_paths=[], logs=[])
    rendered = json.dumps(report).lower()
    for forbidden in ("credential", "token.json", "oauth", "bearer", "nonce", "private"):
        assert forbidden not in rendered


def test_artifact_hashes_present_and_real(tmp_path) -> None:
    result_path = tmp_path / "result_edward-donia.json"
    result_path.write_text(json.dumps(_RESULT))
    report = build_report(
        declaration=_DECLARATION, result=_RESULT, artifact_paths=[result_path], logs=[]
    )
    expected = hashlib.sha256(result_path.read_bytes()).hexdigest()
    assert report["artifact_hashes"][result_path.name] == expected


def test_runtime_summary_reflects_real_timestamps() -> None:
    report = build_report(declaration=_DECLARATION, result=_RESULT, artifact_paths=[], logs=[_LOG])
    assert report["runtime_summary"]["total_steps"] == len(_LOG["steps"])
    assert report["runtime_summary"]["first_timestamp"] == "2026-07-22T08:05:59.000000+00:00"


def test_audit_status_includes_every_sub_game() -> None:
    report = build_report(declaration=_DECLARATION, result=_RESULT, artifact_paths=[], logs=[])
    assert len(report["audit_status"]) == 6
    assert all(entry["audit_ok"] is True for entry in report["audit_status"])

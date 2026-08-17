"""Official course-assigned group-id migration (2026-08-06): our group id
is exactly ``ed%do111`` (the ``%`` is part of the official value, not a
separator or escape sequence). These tests prove the migration is real and
mechanically sound, not just documented: the active committed config
actually uses the new id, the id round-trips through TOML/JSON/artifact
filenames without truncation or reinterpretation, the old provisional id
(``edward-donia``) is rejected by the real consistency check when it is no
longer an expected group id, and no opponent id was fabricated.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.declaration_builder import DeclarationInputs, build_declaration
from police_peer.domain.declaration_seal import declaration_mismatches
from police_peer.domain.gmail_report_schema import build_report
from police_peer.domain.hardware_probe import HardwareInfo
from police_peer.services.artifacts import (
    config_filename,
    declaration_filename,
    log_filename,
    result_filename,
)
from police_peer.shared.config_loader import load_private_config

REPO_ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_GROUP_ID = "ed%do111"

_HW = HardwareInfo(
    operating_system="TestOS",
    platform_detail="TestOS-1.0",
    python_version="3.11.0",
    cpu_model="Test CPU 9000",
    cpu_model_status="detected",
    cpu_cores=8,
    ram_gb=16.0,
    ram_status="detected via sysconf",
    gpu_model=None,
    gpu_available=False,
    gpu_status="not detected",
    vram_gb=None,
    vram_status="not detected",
)


def _inputs(**overrides: object) -> DeclarationInputs:
    base = {
        "role": "police",
        "game_id": f"{OFFICIAL_GROUP_ID}-vs-someone",
        "game_uid": "11111111-2222-3333-4444-555555555555",
        "group_id": OFFICIAL_GROUP_ID,
        "group_name": "Edward-Donia",
        "members": ("Edward Haddad 214083115", "Donia Naser 212810493"),
        "police_repository": "https://example.invalid/police",
        "thief_repository": "https://example.invalid/thief",
        "police_mcp_url": "http://127.0.0.1:8901/mcp",
        "thief_mcp_url": "http://127.0.0.1:8902/mcp",
        "token_budget": 200000,
        "num_sub_games": 6,
        "shared_config_sha256": "a" * 64,
        "code_version": "0.1.0",
        "git_commit": "deadbeef",
        "strategy_class": "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain",
        "banter_provider": "template",
        "hardware": _HW,
    }
    base.update(overrides)
    return DeclarationInputs(**base)  # type: ignore[arg-type]


def test_real_active_toml_configs_use_official_group_id() -> None:
    for rel in ("config/police/game.toml", "config/police_advanced/game.toml"):
        private = load_private_config(REPO_ROOT / rel)
        assert private.game.group_id == OFFICIAL_GROUP_ID, rel


def test_real_active_json_configs_agree_on_official_id_only() -> None:
    # police_advanced stays self-play-only; no opponent id fabricated there.
    data = json.loads((REPO_ROOT / "config" / "police_advanced" / "game.json").read_text())
    assert data["agreed_between"] == [OFFICIAL_GROUP_ID]


def test_real_config_pairing_is_the_negotiated_opponent() -> None:
    # config/police/game.json carries a REAL negotiated opponent (moamteam,
    # 2026-08-17, Gate B) -- not fabricated, see the file's own
    # _agreed_between_note.
    data = json.loads((REPO_ROOT / "config" / "police" / "game.json").read_text())
    assert data["agreed_between"] == [OFFICIAL_GROUP_ID, "moamteam"]


def test_group_id_percent_survives_toml_round_trip(tmp_path: Path) -> None:
    real_toml = (REPO_ROOT / "config" / "police" / "game.toml").read_text()
    assert f'group_id = "{OFFICIAL_GROUP_ID}"' in real_toml
    private = load_private_config(REPO_ROOT / "config" / "police" / "game.toml")
    assert private.game.group_id == OFFICIAL_GROUP_ID
    assert "%" in private.game.group_id
    assert len(private.game.group_id) == 8


def test_group_id_percent_survives_json_round_trip(tmp_path: Path) -> None:
    payload = {"agreed_between": [OFFICIAL_GROUP_ID]}
    path = tmp_path / "roundtrip.json"
    path.write_text(json.dumps(payload))
    reloaded = json.loads(path.read_text())
    assert reloaded["agreed_between"] == [OFFICIAL_GROUP_ID]
    assert reloaded["agreed_between"][0].count("%") == 1


def test_group_id_percent_survives_artifact_filenames() -> None:
    assert declaration_filename(OFFICIAL_GROUP_ID) == "declaration_ed%do111.json"
    assert config_filename(OFFICIAL_GROUP_ID, 3) == "config_ed%do111_g03.json"
    assert log_filename(OFFICIAL_GROUP_ID, 12) == "log_ed%do111_g12.json"
    assert result_filename(OFFICIAL_GROUP_ID) == "result_ed%do111.json"


def test_new_declaration_carries_official_group_id_exactly() -> None:
    decl = build_declaration(_inputs())
    assert decl.group_id == OFFICIAL_GROUP_ID


def test_old_provisional_id_rejected_once_no_longer_expected() -> None:
    decl = build_declaration(_inputs(group_id="edward-donia"))
    reasons = declaration_mismatches(
        decl,
        expected_config_sha256=decl.shared_config_sha256,
        expected_group_ids=frozenset({OFFICIAL_GROUP_ID}),
    )
    assert any("unexpected group_id" in r and "edward-donia" in r for r in reasons)


def test_current_official_id_accepted() -> None:
    decl = build_declaration(_inputs())
    reasons = declaration_mismatches(
        decl,
        expected_config_sha256=decl.shared_config_sha256,
        expected_group_ids=frozenset({OFFICIAL_GROUP_ID}),
    )
    assert not any("group_id" in r for r in reasons)


def test_gmail_report_shows_official_group_id_exactly() -> None:
    declaration = {
        "schema_version": "declaration/2",
        "game_id": OFFICIAL_GROUP_ID,
        "game_uid": "abc-123",
        "group_id": OFFICIAL_GROUP_ID,
        "members": ["Edward Haddad 214083115", "Donia Naser 212810493"],
        "police_repository": "https://github.com/example/police",
        "thief_repository": "https://github.com/example/thief",
        "police_mcp_url": "http://127.0.0.1:8901/mcp",
        "thief_mcp_url": "http://127.0.0.1:8902/mcp",
        "git_commit": "deadbeef" * 5,
        "hardware": {"cpu_model": "Apple M2", "ram_gb": 8.0},
        "strategy_class": "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain",
        "banter_provider": "template",
    }
    result = {
        "game_id": OFFICIAL_GROUP_ID,
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
    report = build_report(declaration=declaration, result=result, artifact_paths=[], logs=[])
    assert report["group_id"] == OFFICIAL_GROUP_ID
    assert report["game_id"] == OFFICIAL_GROUP_ID
    assert len(report["group_id"]) == 8
    # never mangled/escaped into a URL-encoded or truncated form.
    assert "%25" not in json.dumps(report)

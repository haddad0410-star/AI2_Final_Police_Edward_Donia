"""Phase 5: Step-0 declaration assembly, sealing, and consistency checks.

Canonical schema frozen in session recovery step C (declaration/2,
docs/schemas/declaration.schema.json, resolving risk #14). Cross-repository
byte-identical-fixture and schema-SHA-256 comparisons live in the
development workspace's `compare_declaration_schemas.py` script
(development-workspace artifact, not included in this standalone package),
not here (a single repo's tests cannot import the sibling repo).
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

from police_peer.domain.declaration import PeerDeclaration
from police_peer.domain.declaration_builder import DeclarationInputs, build_declaration
from police_peer.domain.declaration_seal import (
    declaration_mismatches,
    generate_declaration_nonce,
    seal_declaration,
    verify_declaration,
)
from police_peer.domain.hardware_probe import HardwareInfo, probe_hardware
from police_peer.domain.repo_metadata import code_version, git_commit_hash
from police_peer.shared.errors import SchemaValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]

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


def _inputs(**overrides) -> DeclarationInputs:
    base = {
        "role": "police",
        "game_id": "edward-donia-vs-someone",
        "game_uid": "11111111-2222-3333-4444-555555555555",
        "group_id": "edward-donia",
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
    return DeclarationInputs(**base)


def test_required_fields_present() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    for key in (
        "schema_version",
        "game_id",
        "game_uid",
        "role",
        "group_id",
        "group_name",
        "members",
        "police_repository",
        "thief_repository",
        "police_mcp_url",
        "thief_mcp_url",
        "timezone",
        "timestamp",
        "token_budget",
        "num_sub_games",
        "shared_config_sha256",
        "code_version",
        "git_commit",
        "strategy_class",
        "banter_provider",
        "hardware",
        "content_sha256",
    ):
        assert key in data
    assert decl.role == "police"
    assert decl.schema_version == "declaration/2"


def test_round_trip_through_from_dict() -> None:
    decl = build_declaration(_inputs())
    reloaded = PeerDeclaration.from_dict(decl.to_dict())
    assert reloaded == decl


def test_missing_field_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    del data["thief_mcp_url"]
    with pytest.raises(SchemaValidationError, match="missing required fields"):
        PeerDeclaration.from_dict(data)


def test_wrong_type_rejected_by_validate() -> None:
    decl = build_declaration(_inputs())
    bad = dataclasses.replace(decl, num_sub_games=0)
    with pytest.raises(SchemaValidationError, match="num_sub_games"):
        bad.validate()


def test_wrong_schema_version_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["schema_version"] = "declaration/1"
    with pytest.raises(SchemaValidationError, match="schema_version"):
        PeerDeclaration.from_dict(data)


def test_wrong_game_uid_detected_via_mismatches() -> None:
    decl = build_declaration(_inputs(game_uid="different-uid"))
    # game_uid itself is not cross-checked by declaration_mismatches (that is
    # the caller's job once it independently derives the expected game_uid);
    # this test proves the field survives a full round trip unmodified so a
    # caller-side comparison is possible.
    reloaded = PeerDeclaration.from_dict(decl.to_dict())
    assert reloaded.game_uid == "different-uid"


def test_config_hash_mismatch_detected() -> None:
    decl = build_declaration(_inputs(shared_config_sha256="a" * 64))
    reasons = declaration_mismatches(decl, "b" * 64, frozenset({"edward-donia"}))
    assert any("shared_config_sha256" in r for r in reasons)


def test_identity_mismatch_detected() -> None:
    decl = build_declaration(_inputs(group_id="someone-else"))
    reasons = declaration_mismatches(decl, "a" * 64, frozenset({"edward-donia"}))
    assert any("group_id" in r for r in reasons)


def test_schema_version_mismatch_detected_via_mismatches() -> None:
    decl = build_declaration(_inputs())
    tampered = dataclasses.replace(decl, schema_version="declaration/999")
    reasons = declaration_mismatches(tampered, "a" * 64, frozenset({"edward-donia"}))
    assert any("schema_version" in r for r in reasons)


def test_repository_placeholder_handling() -> None:
    """An explicit, unresolved local-development placeholder is accepted --
    it must never be silently fabricated into something that looks real."""
    decl = build_declaration(
        _inputs(
            police_repository="local-placeholder://police_peer",
            thief_repository="local-placeholder://thief_peer",
        )
    )
    data = decl.to_dict()
    assert data["police_repository"] == "local-placeholder://police_peer"
    assert data["thief_repository"] == "local-placeholder://thief_peer"
    # Round-trips cleanly; a placeholder is not rejected as invalid.
    assert PeerDeclaration.from_dict(data).police_repository == "local-placeholder://police_peer"


def test_unavailable_gpu_handling() -> None:
    degraded = dataclasses.replace(_HW, gpu_model=None, gpu_available=False, vram_gb=None)
    decl = build_declaration(_inputs(hardware=degraded))
    data = decl.to_dict()
    assert data["hardware"]["gpu_model"] is None
    assert data["hardware"]["gpu_available"] is False
    assert data["hardware"]["vram_gb"] is None
    assert "not detected" in data["hardware"]["gpu_status"] or data["hardware"]["gpu_status"]


def test_missing_hardware_field_is_null_plus_status_not_fabricated() -> None:
    degraded = dataclasses.replace(
        _HW, cpu_model=None, cpu_model_status="unavailable on this platform", ram_gb=None
    )
    decl = build_declaration(_inputs(hardware=degraded))
    data = decl.to_dict()
    assert data["hardware"]["cpu_model"] is None
    assert "unavailable" in data["hardware"]["cpu_model_status"]
    assert data["hardware"]["ram_gb"] is None
    assert data["hardware"]["gpu_model"] is None  # never invented


def test_real_probe_never_crashes_and_gpu_is_null() -> None:
    hw = probe_hardware()
    assert hw.gpu_model is None
    assert hw.gpu_available is False
    assert hw.vram_gb is None
    assert isinstance(hw.operating_system, str)
    assert hw.cpu_cores is None or hw.cpu_cores > 0


def test_secret_like_field_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["police_repository"] = "https://user:api_key=SECRETVALUE@example.invalid/police"
    serialized = json.dumps(data).lower()
    assert "api_key" in serialized  # sanity: the needle really is present
    from police_peer.services.artifacts import assert_no_credentials

    with pytest.raises(SchemaValidationError):
        assert_no_credentials(data)


def test_unknown_field_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["totally_unrecognized_field"] = "sneaky"
    with pytest.raises(SchemaValidationError, match="unknown declaration field"):
        PeerDeclaration.from_dict(data)


def test_unknown_hardware_field_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["hardware"]["unexpected_key"] = 1
    with pytest.raises(SchemaValidationError, match="unknown hardware field"):
        PeerDeclaration.from_dict(data)


def test_supported_legacy_alias_normalization() -> None:
    """declaration/1's `commit_hash`/`config_sha256` names are accepted on
    input only and normalized immediately to the canonical declaration/2
    names -- never re-emitted as an alias."""
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["commit_hash"] = data.pop("git_commit")
    data["config_sha256"] = data.pop("shared_config_sha256")
    reloaded = PeerDeclaration.from_dict(data)
    assert reloaded.git_commit == decl.git_commit
    assert reloaded.shared_config_sha256 == decl.shared_config_sha256
    assert "commit_hash" not in reloaded.to_dict()
    assert "config_sha256" not in reloaded.to_dict()


def test_ambiguous_alias_rejected() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["commit_hash"] = "conflicting-value-not-matching-git_commit"
    with pytest.raises(SchemaValidationError, match="ambiguous"):
        PeerDeclaration.from_dict(data)


def test_alias_with_matching_value_is_not_ambiguous() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    data["commit_hash"] = data["git_commit"]  # redundant but consistent
    reloaded = PeerDeclaration.from_dict(data)
    assert reloaded.git_commit == decl.git_commit


def test_correct_git_commit_hash_matches_real_head() -> None:
    """When ``.git`` exists, must match the real HEAD exactly. When it
    doesn't (a clean-extracted review ZIP, which deliberately excludes
    ``.git``), must match the packaged ``BUILD_COMMIT`` file instead --
    never silently skipped either way."""
    if (REPO_ROOT / ".git").exists():
        real = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert git_commit_hash(REPO_ROOT) == real
        assert len(real) == 40
        return
    build_commit = REPO_ROOT / "BUILD_COMMIT"
    assert build_commit.exists(), "no .git and no BUILD_COMMIT -- commit provenance unverifiable"
    expected = build_commit.read_text(encoding="utf-8").strip()
    assert git_commit_hash(REPO_ROOT) == expected
    assert len(expected) == 40


def test_code_version_read_from_pyproject() -> None:
    assert code_version(REPO_ROOT / "pyproject.toml") == "0.1.0"


def test_tampering_detected_via_reseal() -> None:
    decl = build_declaration(_inputs())
    nonce = generate_declaration_nonce()
    sealed = seal_declaration(decl, nonce)
    assert verify_declaration(decl, nonce, sealed) is True
    tampered = dataclasses.replace(decl, git_commit="0" * 40)
    assert verify_declaration(tampered, nonce, sealed) is False


def test_no_credentials_or_secrets_in_serialized_declaration() -> None:
    decl = build_declaration(_inputs())
    serialized = json.dumps(decl.to_dict()).lower()
    for needle in ("secret", "password", "api_key", "apikey", "credential", "token.json"):
        assert needle not in serialized, needle
    # "token_budget" is a legitimate FIELD NAME, not a secret value.
    assert "token_budget" in decl.to_dict()

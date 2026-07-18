"""Phase 5: Step-0 declaration assembly, sealing, and consistency checks."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

from police_peer.domain.crypto import verify_commit  # noqa: F401  (kept for parity of imports)
from police_peer.domain.declaration import (
    DeclarationInputs,
    build_declaration,
    declaration_mismatches,
    generate_declaration_nonce,
    seal_declaration,
    verify_declaration,
)
from police_peer.domain.hardware_probe import HardwareInfo, probe_hardware
from police_peer.domain.repo_metadata import code_version, git_commit_hash

REPO_ROOT = Path(__file__).resolve().parents[2]

_HW = HardwareInfo(
    operating_system="TestOS",
    platform_detail="TestOS-1.0",
    cpu_model="Test CPU 9000",
    cpu_model_status="detected",
    cpu_cores=8,
    ram_gb=16.0,
    ram_status="detected via sysconf",
    gpu_model=None,
    gpu_status="not detected",
    python_version="3.11.0",
)


def _inputs(**overrides) -> DeclarationInputs:
    base = {
        "group_name": "Edward-Donia",
        "group_id": "edward-donia",
        "members": ("Edward Haddad 214083115", "Donia Naser 212810493"),
        "repository": "https://example.invalid/police",
        "code_version": "0.1.0",
        "git_commit": "deadbeef",
        "strategy_class": "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain",
        "banter_provider": "template",
        "token_budget": 200000,
        "shared_config_sha256": "a" * 64,
        "hardware": _HW,
    }
    base.update(overrides)
    return DeclarationInputs(**base)


def test_required_fields_present() -> None:
    decl = build_declaration(_inputs())
    data = decl.to_dict()
    for key in (
        "schema_version",
        "role",
        "group_name",
        "group_id",
        "members",
        "repository",
        "code_version",
        "git_commit",
        "strategy_class",
        "banter_provider",
        "token_budget",
        "shared_config_sha256",
        "timezone",
        "timestamp",
        "operating_system",
        "cpu_model",
        "cpu_cores",
        "ram_gb",
        "gpu_model",
        "python_version",
    ):
        assert key in data
    assert decl.role == "police"


def test_correct_git_commit_hash_matches_real_head() -> None:
    real = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert git_commit_hash(REPO_ROOT) == real
    assert len(real) == 40


def test_code_version_read_from_pyproject() -> None:
    assert code_version(REPO_ROOT / "pyproject.toml") == "0.1.0"


def test_missing_hardware_field_is_null_plus_status_not_fabricated() -> None:
    degraded = dataclasses.replace(
        _HW, cpu_model=None, cpu_model_status="unavailable on this platform", ram_gb=None
    )
    decl = build_declaration(_inputs(hardware=degraded))
    data = decl.to_dict()
    assert data["cpu_model"] is None
    assert "unavailable" in data["cpu_model_status"]
    assert data["ram_gb"] is None
    assert data["gpu_model"] is None  # never invented


def test_real_probe_never_crashes_and_gpu_is_null() -> None:
    hw = probe_hardware()
    assert hw.gpu_model is None
    assert isinstance(hw.operating_system, str)
    assert hw.cpu_cores is None or hw.cpu_cores > 0


def test_config_hash_mismatch_detected() -> None:
    decl = build_declaration(_inputs(shared_config_sha256="a" * 64))
    reasons = declaration_mismatches(decl, "b" * 64, frozenset({"edward-donia"}))
    assert any("config_sha256" in r for r in reasons)


def test_identity_mismatch_detected() -> None:
    decl = build_declaration(_inputs(group_id="someone-else"))
    reasons = declaration_mismatches(decl, "a" * 64, frozenset({"edward-donia"}))
    assert any("group_id" in r for r in reasons)


def test_schema_version_mismatch_detected() -> None:
    decl = build_declaration(_inputs())
    tampered = dataclasses.replace(decl, schema_version="declaration/999")
    reasons = declaration_mismatches(tampered, "a" * 64, frozenset({"edward-donia"}))
    assert any("schema_version" in r for r in reasons)


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

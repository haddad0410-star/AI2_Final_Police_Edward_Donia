"""Step-0 peer declaration (Batch 2, Phase 5).

Assembles the sealed, exchanged pre-game declaration from real, non-fabricated
sources: private identity config, shared config hash, accurate git commit,
pyproject version, and best-effort hardware probing (null + status where a value
cannot be genuinely determined). ``game_id``/``game_uid`` are left for the
caller to fill -- this module does not own game-id derivation. The declaration
carries no credentials or secrets.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from police_peer.domain.hardware_probe import HardwareInfo, probe_hardware
from police_peer.shared.canonical_json import canonical_sha256_hex
from police_peer.shared.errors import SchemaValidationError

SCHEMA_VERSION = "declaration/1"


@dataclass(frozen=True, slots=True)
class PeerDeclaration:
    """The full Step-0 declaration for this peer (one per series)."""

    group_name: str
    group_id: str
    members: tuple[str, ...]
    repository: str
    code_version: str
    git_commit: str
    strategy_class: str
    banter_provider: str
    token_budget: int
    shared_config_sha256: str
    hardware: HardwareInfo
    timezone: str
    timestamp: str
    role: str = "police"
    schema_version: str = SCHEMA_VERSION
    game_id: str | None = None
    game_uid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """A flat, JSON-safe, canonical-ready dict of the whole declaration."""
        hw = self.hardware
        return {
            "schema_version": self.schema_version,
            "game_id": self.game_id,
            "game_uid": self.game_uid,
            "role": self.role,
            "group_name": self.group_name,
            "group_id": self.group_id,
            "members": list(self.members),
            "repository": self.repository,
            "code_version": self.code_version,
            "git_commit": self.git_commit,
            "strategy_class": self.strategy_class,
            "banter_provider": self.banter_provider,
            "token_budget": self.token_budget,
            "shared_config_sha256": self.shared_config_sha256,
            "timezone": self.timezone,
            "timestamp": self.timestamp,
            "operating_system": hw.operating_system,
            "platform_detail": hw.platform_detail,
            "cpu_model": hw.cpu_model,
            "cpu_model_status": hw.cpu_model_status,
            "cpu_cores": hw.cpu_cores,
            "ram_gb": hw.ram_gb,
            "ram_status": hw.ram_status,
            "gpu_model": hw.gpu_model,
            "gpu_status": hw.gpu_status,
            "python_version": hw.python_version,
        }

    def validate(self) -> None:
        """Self-consistency check before this declaration is saved as the
        declaration_<game_id>.json artifact (Phase 11) -- mirrors the other
        three artifact models' minimal ``validate()`` contract."""
        if not self.group_id or not self.group_name:
            raise SchemaValidationError("declaration needs group_id and group_name")
        if len(self.shared_config_sha256) != 64:
            raise SchemaValidationError("shared_config_sha256 must be a 64-char digest")


@dataclass(frozen=True, slots=True)
class DeclarationInputs:
    """The non-hardware inputs a caller supplies to build a declaration."""

    group_name: str
    group_id: str
    members: tuple[str, ...]
    repository: str
    code_version: str
    git_commit: str
    strategy_class: str
    banter_provider: str
    token_budget: int
    shared_config_sha256: str
    game_id: str | None = None
    game_uid: str | None = None
    hardware: HardwareInfo | None = field(default=None)


def build_declaration(inputs: DeclarationInputs) -> PeerDeclaration:
    """Build a declaration, probing hardware unless one was injected (for tests)."""
    hardware = inputs.hardware if inputs.hardware is not None else probe_hardware()
    now = datetime.now(UTC)
    return PeerDeclaration(
        group_name=inputs.group_name,
        group_id=inputs.group_id,
        members=inputs.members,
        repository=inputs.repository,
        code_version=inputs.code_version,
        git_commit=inputs.git_commit,
        strategy_class=inputs.strategy_class,
        banter_provider=inputs.banter_provider,
        token_budget=inputs.token_budget,
        shared_config_sha256=inputs.shared_config_sha256,
        hardware=hardware,
        timezone=str(now.astimezone().tzinfo),
        timestamp=now.isoformat(),
        game_id=inputs.game_id,
        game_uid=inputs.game_uid,
    )


def seal_declaration(declaration: PeerDeclaration, nonce: str) -> str:
    """Commit hash over the declaration + a hidden nonce (Phase 4 canonical hash)."""
    payload = {**declaration.to_dict(), "nonce": nonce}
    return canonical_sha256_hex(payload)


def verify_declaration(declaration: PeerDeclaration, nonce: str, expected_hash: str) -> bool:
    """Constant-time check that a declaration reseals to ``expected_hash``."""
    return secrets.compare_digest(seal_declaration(declaration, nonce), expected_hash)


def generate_declaration_nonce() -> str:
    """A fresh CSPRNG nonce for sealing the declaration (never a timestamp)."""
    return secrets.token_hex(32)


def declaration_mismatches(
    declaration: PeerDeclaration,
    expected_config_sha256: str,
    expected_group_ids: frozenset[str],
    expected_schema_version: str = SCHEMA_VERSION,
) -> list[str]:
    """Return human-readable reasons an incoming declaration is inconsistent."""
    reasons: list[str] = []
    if declaration.shared_config_sha256 != expected_config_sha256:
        reasons.append("shared_config_sha256 mismatch")
    if declaration.group_id not in expected_group_ids:
        reasons.append(f"unexpected group_id {declaration.group_id!r}")
    if declaration.schema_version != expected_schema_version:
        reasons.append("schema_version mismatch")
    return reasons

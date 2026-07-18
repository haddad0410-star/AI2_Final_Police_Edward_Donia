"""Step-0 peer declaration (Batch 2, Phase 5; canonical schema frozen in
session recovery step C -- see docs/schemas/declaration.schema.json,
byte-identical to the Thief repo's copy, resolving risk #14's field-name
divergence).

The declaration carries no credentials or secrets. Parsing (``from_dict``,
alias normalization) lives in ``declaration_parsing.py``; assembly from
live inputs lives in ``declaration_builder.py``; sealing/mismatch-checking
lives in ``declaration_seal.py`` -- split out to stay under the 150-line cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from police_peer.domain.hardware_probe import HardwareInfo
from police_peer.shared.errors import SchemaValidationError

SCHEMA_VERSION = "declaration/2"

#: declaration/1-era field names accepted as unambiguous input aliases,
#: normalized immediately to the canonical declaration/2 name. Never
#: emitted by to_dict() -- canonical output uses exactly one name per field.
ALIASES = {"commit_hash": "git_commit", "config_sha256": "shared_config_sha256"}

HARDWARE_FIELDS = (
    "operating_system", "platform_detail", "python_version", "cpu_model",
    "cpu_model_status", "cpu_cores", "ram_gb", "ram_status", "gpu_model",
    "gpu_available", "gpu_status", "vram_gb", "vram_status",
)  # fmt: skip

TOP_LEVEL_FIELDS = (
    "schema_version", "game_id", "game_uid", "role", "group_id", "group_name",
    "members", "police_repository", "thief_repository", "police_mcp_url",
    "thief_mcp_url", "timezone", "timestamp", "token_budget", "num_sub_games",
    "shared_config_sha256", "code_version", "git_commit", "strategy_class",
    "banter_provider", "hardware", "content_sha256",
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class PeerDeclaration:
    """The full, canonical Step-0 declaration for this peer (one per series)."""

    schema_version: str
    game_id: str
    game_uid: str
    role: str
    group_id: str
    group_name: str
    members: tuple[str, ...]
    police_repository: str
    thief_repository: str
    police_mcp_url: str
    thief_mcp_url: str
    timezone: str
    timestamp: str
    token_budget: int
    num_sub_games: int
    shared_config_sha256: str
    code_version: str
    git_commit: str
    strategy_class: str
    banter_provider: str
    hardware: HardwareInfo
    content_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Canonical JSON-safe dict -- exactly one key per field, never an alias."""
        return {
            "schema_version": self.schema_version,
            "game_id": self.game_id,
            "game_uid": self.game_uid,
            "role": self.role,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "members": list(self.members),
            "police_repository": self.police_repository,
            "thief_repository": self.thief_repository,
            "police_mcp_url": self.police_mcp_url,
            "thief_mcp_url": self.thief_mcp_url,
            "timezone": self.timezone,
            "timestamp": self.timestamp,
            "token_budget": self.token_budget,
            "num_sub_games": self.num_sub_games,
            "shared_config_sha256": self.shared_config_sha256,
            "code_version": self.code_version,
            "git_commit": self.git_commit,
            "strategy_class": self.strategy_class,
            "banter_provider": self.banter_provider,
            "hardware": hardware_to_dict(self.hardware),
            "content_sha256": self.content_sha256,
        }

    def validate(self) -> None:
        if not self.group_id or not self.group_name:
            raise SchemaValidationError("declaration needs group_id and group_name")
        if len(self.shared_config_sha256) != 64:
            raise SchemaValidationError("shared_config_sha256 must be a 64-char digest")
        if self.schema_version != SCHEMA_VERSION:
            raise SchemaValidationError(f"unsupported schema_version {self.schema_version!r}")
        if self.role not in ("police", "thief"):
            raise SchemaValidationError(f"role must be police or thief, got {self.role!r}")
        if self.num_sub_games < 1:
            raise SchemaValidationError("num_sub_games must be >= 1")
        if len(self.content_sha256) != 64:
            raise SchemaValidationError("content_sha256 must be a 64-char digest")

    @classmethod
    def from_dict(cls, data: dict) -> PeerDeclaration:
        from police_peer.domain.declaration_parsing import parse_declaration

        return parse_declaration(data)


def hardware_to_dict(hw: HardwareInfo) -> dict[str, Any]:
    return {name: getattr(hw, name) for name in HARDWARE_FIELDS}

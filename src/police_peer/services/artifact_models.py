"""Dataclass models for three of the four standardized JSON artifacts.

(The declaration artifact reuses ``domain.declaration.PeerDeclaration``.) Chosen
approach: plain dataclasses with explicit ``validate``/``from_dict`` methods and
canonical-JSON output -- no extra runtime dependency (documented in
docs/ARCHITECTURE.md). Every artifact carries the same ``game_uid`` so the four
files can never be mixed across games.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from police_peer.shared.errors import SchemaValidationError

CONFIG_SCHEMA = "config/1"
LOG_SCHEMA = "log/1"
RESULT_SCHEMA = "result/1"


def _require(data: dict, keys: tuple[str, ...]) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise SchemaValidationError(f"artifact missing required fields: {missing}")


@dataclass(frozen=True, slots=True)
class ConfigArtifact:
    """The agreed Appendix-F terms + config hash for one sub-game."""

    game_uid: str
    game_id: str
    sub_game_number: int
    config_sha256: str
    terms: dict[str, Any]
    schema_version: str = CONFIG_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "game_uid": self.game_uid,
            "game_id": self.game_id,
            "sub_game_number": self.sub_game_number,
            "config_sha256": self.config_sha256,
            "terms": self.terms,
        }

    def validate(self) -> None:
        if not self.game_uid or not self.game_id:
            raise SchemaValidationError("config artifact needs game_uid and game_id")
        if len(self.config_sha256) != 64:
            raise SchemaValidationError("config_sha256 must be a 64-char digest")

    @classmethod
    def from_dict(cls, data: dict) -> ConfigArtifact:
        _require(data, ("game_uid", "game_id", "sub_game_number", "config_sha256", "terms"))
        artifact = cls(
            game_uid=data["game_uid"],
            game_id=data["game_id"],
            sub_game_number=int(data["sub_game_number"]),
            config_sha256=data["config_sha256"],
            terms=data["terms"],
            schema_version=data.get("schema_version", CONFIG_SCHEMA),
        )
        artifact.validate()
        return artifact


@dataclass(frozen=True, slots=True)
class LogArtifact:
    """One sub-game's sealed step records (nonces revealed) + audit result."""

    game_uid: str
    game_id: str
    sub_game_number: int
    steps: list[dict[str, Any]]
    audit_verdict: str
    audit_reason: str
    schema_version: str = LOG_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "game_uid": self.game_uid,
            "game_id": self.game_id,
            "sub_game_number": self.sub_game_number,
            "steps": self.steps,
            "audit_verdict": self.audit_verdict,
            "audit_reason": self.audit_reason,
        }

    def validate(self) -> None:
        if not self.game_uid:
            raise SchemaValidationError("log artifact needs game_uid")
        if self.audit_verdict not in ("verified", "tamper_forfeit"):
            raise SchemaValidationError(f"bad audit_verdict {self.audit_verdict!r}")

    @classmethod
    def from_dict(cls, data: dict) -> LogArtifact:
        _require(data, ("game_uid", "game_id", "sub_game_number", "steps", "audit_verdict"))
        artifact = cls(
            game_uid=data["game_uid"],
            game_id=data["game_id"],
            sub_game_number=int(data["sub_game_number"]),
            steps=list(data["steps"]),
            audit_verdict=data["audit_verdict"],
            audit_reason=data.get("audit_reason", ""),
            schema_version=data.get("schema_version", LOG_SCHEMA),
        )
        artifact.validate()
        return artifact


@dataclass(frozen=True, slots=True)
class ResultArtifact:
    """Whole-series scores, winner per sub-game, and mutual-audit outcome."""

    game_uid: str
    game_id: str
    git_commit: str
    group_id: str
    config_sha256: str
    sub_games: list[dict[str, Any]]
    police_total: int
    thief_total: int
    agreement_status: str
    agreed: bool
    schema_version: str = RESULT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "game_uid": self.game_uid,
            "game_id": self.game_id,
            "git_commit": self.git_commit,
            "group_id": self.group_id,
            "config_sha256": self.config_sha256,
            "sub_games": self.sub_games,
            "police_total": self.police_total,
            "thief_total": self.thief_total,
            "agreement_status": self.agreement_status,
            "agreed": self.agreed,
        }

    def validate(self) -> None:
        if not self.game_uid or not self.group_id:
            raise SchemaValidationError("result artifact needs game_uid and group_id")
        if len(self.config_sha256) != 64:
            raise SchemaValidationError("config_sha256 must be a 64-char digest")

    @classmethod
    def from_dict(cls, data: dict) -> ResultArtifact:
        _require(
            data,
            ("game_uid", "game_id", "git_commit", "group_id", "config_sha256", "sub_games"),
        )
        artifact = cls(
            game_uid=data["game_uid"],
            game_id=data["game_id"],
            git_commit=data["git_commit"],
            group_id=data["group_id"],
            config_sha256=data["config_sha256"],
            sub_games=list(data["sub_games"]),
            police_total=int(data.get("police_total", 0)),
            thief_total=int(data.get("thief_total", 0)),
            agreement_status=data.get("agreement_status", ""),
            agreed=bool(data.get("agreed", False)),
            schema_version=data.get("schema_version", RESULT_SCHEMA),
        )
        artifact.validate()
        return artifact

"""Assemble a canonical PeerDeclaration from live, non-fabricated inputs
(session recovery step C). Split out of ``declaration.py`` to stay under
the 150-line cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from police_peer.domain.declaration import SCHEMA_VERSION, PeerDeclaration, hardware_to_dict
from police_peer.domain.hardware_probe import HardwareInfo, probe_hardware
from police_peer.shared.canonical_json import canonical_sha256_hex


@dataclass(frozen=True, slots=True)
class DeclarationInputs:
    """The non-hardware inputs a caller supplies to build a declaration."""

    role: str
    game_id: str
    game_uid: str
    group_id: str
    group_name: str
    members: tuple[str, ...]
    police_repository: str
    thief_repository: str
    police_mcp_url: str
    thief_mcp_url: str
    token_budget: int
    num_sub_games: int
    shared_config_sha256: str
    code_version: str
    git_commit: str
    strategy_class: str
    banter_provider: str
    hardware: HardwareInfo | None = field(default=None)


def build_declaration(inputs: DeclarationInputs, *, now: datetime | None = None) -> PeerDeclaration:
    """Build a declaration, probing hardware unless one was injected (for tests).

    ``content_sha256`` is computed over every OTHER field's canonical JSON --
    a documented commitment representation the replay verifier can
    recompute and compare independently of the separate nonce-based Step-0
    commit/reveal exchange (``declaration_seal.py``).
    """
    hardware = inputs.hardware if inputs.hardware is not None else probe_hardware()
    stamp = now or datetime.now(UTC)
    timezone = str(stamp.astimezone().tzinfo)
    timestamp = stamp.isoformat()
    pre_hash_fields = {
        "schema_version": SCHEMA_VERSION,
        "game_id": inputs.game_id,
        "game_uid": inputs.game_uid,
        "role": inputs.role,
        "group_id": inputs.group_id,
        "group_name": inputs.group_name,
        "members": list(inputs.members),
        "police_repository": inputs.police_repository,
        "thief_repository": inputs.thief_repository,
        "police_mcp_url": inputs.police_mcp_url,
        "thief_mcp_url": inputs.thief_mcp_url,
        "timezone": timezone,
        "timestamp": timestamp,
        "token_budget": inputs.token_budget,
        "num_sub_games": inputs.num_sub_games,
        "shared_config_sha256": inputs.shared_config_sha256,
        "code_version": inputs.code_version,
        "git_commit": inputs.git_commit,
        "strategy_class": inputs.strategy_class,
        "banter_provider": inputs.banter_provider,
        "hardware": hardware_to_dict(hardware),
    }
    return PeerDeclaration(
        schema_version=SCHEMA_VERSION,
        game_id=inputs.game_id,
        game_uid=inputs.game_uid,
        role=inputs.role,
        group_id=inputs.group_id,
        group_name=inputs.group_name,
        members=inputs.members,
        police_repository=inputs.police_repository,
        thief_repository=inputs.thief_repository,
        police_mcp_url=inputs.police_mcp_url,
        thief_mcp_url=inputs.thief_mcp_url,
        timezone=timezone,
        timestamp=timestamp,
        token_budget=inputs.token_budget,
        num_sub_games=inputs.num_sub_games,
        shared_config_sha256=inputs.shared_config_sha256,
        code_version=inputs.code_version,
        git_commit=inputs.git_commit,
        strategy_class=inputs.strategy_class,
        banter_provider=inputs.banter_provider,
        hardware=hardware,
        content_sha256=canonical_sha256_hex(pre_hash_fields),
    )

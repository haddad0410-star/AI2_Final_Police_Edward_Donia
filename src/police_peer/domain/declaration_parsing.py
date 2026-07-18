"""Parsing/normalization for the canonical Step-0 declaration (session
recovery step C). Split out of ``declaration.py`` to stay under the
150-line cap.
"""

from __future__ import annotations

from police_peer.domain.declaration import (
    ALIASES,
    HARDWARE_FIELDS,
    TOP_LEVEL_FIELDS,
    PeerDeclaration,
)
from police_peer.domain.hardware_probe import HardwareInfo
from police_peer.shared.errors import SchemaValidationError


def parse_declaration(data: dict) -> PeerDeclaration:
    """Parse a declaration dict, normalizing supported legacy aliases and
    rejecting unknown fields -- a schema this security-sensitive must not
    silently accept a field it does not recognize."""
    normalized = _normalize_aliases(dict(data))
    unknown = set(normalized) - set(TOP_LEVEL_FIELDS)
    if unknown:
        raise SchemaValidationError(f"unknown declaration field(s): {sorted(unknown)}")
    missing = [f for f in TOP_LEVEL_FIELDS if f not in normalized]
    if missing:
        raise SchemaValidationError(f"declaration missing required fields: {missing}")
    hw_raw = normalized["hardware"]
    hw_unknown = set(hw_raw) - set(HARDWARE_FIELDS)
    if hw_unknown:
        raise SchemaValidationError(f"unknown hardware field(s): {sorted(hw_unknown)}")
    decl = PeerDeclaration(
        schema_version=normalized["schema_version"],
        game_id=normalized["game_id"],
        game_uid=normalized["game_uid"],
        role=normalized["role"],
        group_id=normalized["group_id"],
        group_name=normalized["group_name"],
        members=tuple(normalized["members"]),
        police_repository=normalized["police_repository"],
        thief_repository=normalized["thief_repository"],
        police_mcp_url=normalized["police_mcp_url"],
        thief_mcp_url=normalized["thief_mcp_url"],
        timezone=normalized["timezone"],
        timestamp=normalized["timestamp"],
        token_budget=int(normalized["token_budget"]),
        num_sub_games=int(normalized["num_sub_games"]),
        shared_config_sha256=normalized["shared_config_sha256"],
        code_version=normalized["code_version"],
        git_commit=normalized["git_commit"],
        strategy_class=normalized["strategy_class"],
        banter_provider=normalized["banter_provider"],
        hardware=HardwareInfo(**{k: hw_raw[k] for k in HARDWARE_FIELDS}),
        content_sha256=normalized["content_sha256"],
    )
    decl.validate()
    return decl


def _normalize_aliases(data: dict) -> dict:
    """Accept declaration/1-era aliases on input only, normalized immediately.
    An alias present alongside a DIFFERING canonical value is ambiguous and
    rejected outright; an alias with no canonical present (or an identical
    value) is normalized silently."""
    for alias, canonical in ALIASES.items():
        if alias not in data:
            continue
        alias_value = data.pop(alias)
        if canonical in data and data[canonical] != alias_value:
            raise SchemaValidationError(
                f"ambiguous declaration input: {alias!r}={alias_value!r} conflicts with "
                f"{canonical!r}={data.get(canonical)!r}"
            )
        data.setdefault(canonical, alias_value)
    return data

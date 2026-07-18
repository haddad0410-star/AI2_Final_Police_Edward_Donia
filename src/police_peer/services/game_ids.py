"""Deterministic game_id / game_uid derivation (protocol_contract.md 3.1).

Both peers derive these independently from data they already hold -- the sorted
group ids plus the agreed config hash -- so no extra round-trip is needed and
all four JSON artifacts share one identity.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable


def derive_game_id(group_ids: Iterable[str]) -> str:
    """``"<group_a>-vs-<group_b>"`` (sorted); a single id for local self-play."""
    ids = sorted(group_ids)
    return "-vs-".join(ids) if len(ids) > 1 else (ids[0] if ids else "unknown")


def derive_game_uid(config_sha256: str, group_ids: Iterable[str]) -> str:
    """A stable UUID over the config hash + sorted group ids."""
    seed = config_sha256 + "|" + "-".join(sorted(group_ids))
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))

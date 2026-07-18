"""Load a full artifact set from a directory for the replay verifier (Phase 12).

Pure file I/O only -- no repository-private runtime state is consulted, so the
verifier can audit any artifact directory (ours or, in principle, an opponent's
published set).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from police_peer.services.artifacts import load_json


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    """Every artifact discovered in a directory, parsed as plain dicts."""

    declaration: dict | None
    configs: list[dict]
    logs: list[dict]
    result: dict | None

    def all_dicts(self) -> list[dict]:
        """Every parsed artifact (for cross-file game_uid checks)."""
        items = [*self.configs, *self.logs]
        if self.declaration is not None:
            items.append(self.declaration)
        if self.result is not None:
            items.append(self.result)
        return items


def _one(paths: list[Path]) -> dict | None:
    return load_json(paths[0]) if paths else None


def load_bundle(directory: Path) -> ReplayBundle:
    """Discover and parse declaration / configs / logs / result in ``directory``."""
    return ReplayBundle(
        declaration=_one(sorted(directory.glob("declaration_*.json"))),
        configs=[load_json(p) for p in sorted(directory.glob("config_*.json"))],
        logs=[load_json(p) for p in sorted(directory.glob("log_*.json"))],
        result=_one(sorted(directory.glob("result_*.json"))),
    )

"""Batch 4B Task 3/4/9: graphical replay viewer's data layer -- now capable
of FULL BILATERAL verification. The actual verification logic lives in
``services.bilateral_verify`` (shared with the Gmail report gate, Task 9,
so neither layer duplicates it); this module only shapes that result plus
the per-step display data (``ReplaySubGame``) for the viewer.

Legacy note (Rule 10): artifacts sealed under the OLD, pre-Batch-4B
per-repo schemas (Police's ``commit-reveal/2``, Thief's ``sealed-turn/2``)
remain readable for path/hint DISPLAY, but a genuinely cross-repo LEGACY
record can still not be cryptographically re-verified by the other side
-- this is an explicit, honestly-labeled legacy limitation, never
silently hidden, and never applied to current ``commitment/1`` records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from police_peer.gui.replay_steps import ReplaySubGame, build_sub_game
from police_peer.services.bilateral_verify import (
    LEGACY_VERDICT,
    SideVerification,
    verify_bilateral,
)
from police_peer.services.replay_loader import load_bundle

__all__ = ["LEGACY_VERDICT", "ReplayViewModel", "SideVerification", "build_replay_view"]


@dataclass(frozen=True, slots=True)
class ReplayViewModel:
    police: SideVerification
    thief: SideVerification
    verdict: str
    verification_ok: bool
    full_bilateral_verification: bool
    declaration: dict | None
    config_sha256_prefix: str
    sub_games: tuple[ReplaySubGame, ...] = field(default_factory=tuple)


def build_replay_view(police_dir: Path, thief_dir: Path) -> ReplayViewModel:
    """Build the display model from BOTH sides' independently-written
    artifact sets, verifying EACH side with this repo's own real verifier.
    ``full_bilateral_verification`` is true only when BOTH sides were
    independently verified AND both report VERIFIED."""
    police_side, thief_side, full_bilateral = verify_bilateral(police_dir, thief_dir)
    police_bundle = load_bundle(police_dir)
    thief_bundle = load_bundle(thief_dir)
    police_logs = {log.get("sub_game_number"): log for log in police_bundle.logs}
    thief_logs = {log.get("sub_game_number"): log for log in thief_bundle.logs}
    result = police_bundle.result or thief_bundle.result or {}
    sub_games = tuple(
        build_sub_game(entry, police_logs, thief_logs) for entry in result.get("sub_games", [])
    )
    if full_bilateral:
        verdict, verification_ok = "VERIFIED", True
    else:
        verdict = police_side.verdict if not police_side.ok else thief_side.verdict
        verification_ok = police_side.ok and (
            thief_side.ok if thief_side.independently_verified else True
        )
    return ReplayViewModel(
        police=police_side,
        thief=thief_side,
        verdict=verdict,
        verification_ok=verification_ok,
        full_bilateral_verification=full_bilateral,
        declaration=police_bundle.declaration or thief_bundle.declaration,
        config_sha256_prefix=str(result.get("config_sha256", ""))[:8],
        sub_games=sub_games,
    )

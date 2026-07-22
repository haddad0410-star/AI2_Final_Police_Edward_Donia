"""Batch 4A Task 7/8: graphical replay viewer's data layer. Reuses the
REAL, existing, independent replay-verification engine
(``services.replay_verifier.verify_replay``/``services.replay_loader.load_bundle``)
unmodified -- this module never recomputes a hash or re-implements any
cryptographic check itself; it only reshapes the SAME verified bundles for
display. No Tkinter import here, so this is headlessly testable (Task 8).

Unlike the live view model, both true trajectories are permitted here --
this module only ever reads FINALIZED, audited artifact files from disk
(each side's OWN independently-written 14-file set), never live private
runtime memory. Showing BOTH sides' true paths together requires BOTH
sides' artifact directories, since each side's own sealed log only ever
records its own true position -- reading the opponent's already-published
JSON artifact format is not a code dependency on the opponent's package,
just a public data-format parse (same as any third-party audit tool would
do).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from police_peer.gui.replay_steps import ReplaySubGame, build_sub_game
from police_peer.services.replay_loader import load_bundle
from police_peer.services.replay_verifier import ReplayReport, verify_replay


@dataclass(frozen=True, slots=True)
class SideVerification:
    directory: str
    verdict: str
    ok: bool
    findings: tuple[str, ...]
    independently_verified: bool


@dataclass(frozen=True, slots=True)
class ReplayViewModel:
    police: SideVerification
    thief: SideVerification
    verdict: str
    verification_ok: bool
    declaration: dict | None
    config_sha256_prefix: str
    sub_games: tuple[ReplaySubGame, ...] = field(default_factory=tuple)


def _own_side(directory: Path) -> tuple[SideVerification, dict]:
    """Police's own artifacts: cryptographically verified for real by the
    real, unmodified engine (this repo's own crypto module produced them)."""
    report: ReplayReport = verify_replay(directory)
    bundle = load_bundle(directory)
    side = SideVerification(
        directory=str(directory),
        verdict=report.verdict,
        ok=report.ok,
        findings=tuple(report.findings),
        independently_verified=True,
    )
    return side, bundle


def _opponent_side(directory: Path) -> tuple[SideVerification, dict]:
    """Thief's artifacts use an independently-built sealing schema
    (``sealed-turn/2`` vs this repo's ``commit-reveal/2``) -- Police's own
    ``verify_replay`` recomputes commitment hashes using ITS OWN
    canonicalization and would report a false TAMPERED on genuinely valid
    Thief data (a real cross-schema incompatibility found while building
    this viewer, not a tamper). Never claim a verdict this repo's crypto
    module cannot actually compute: load-only, for display, with an
    honest ``independently_verified=False``. The real verdict for this
    side is `thief_peer`'s own ``verify-replay``/replay viewer."""
    bundle = load_bundle(directory)
    side = SideVerification(
        directory=str(directory),
        verdict="NOT_INDEPENDENTLY_VERIFIED_FROM_THIS_SIDE",
        ok=True,
        findings=(),
        independently_verified=False,
    )
    return side, bundle


def build_replay_view(police_dir: Path, thief_dir: Path) -> ReplayViewModel:
    """Build the display model from BOTH sides' independently-written
    artifact sets. Only Police's OWN artifacts are cryptographically
    re-verified here (by the real, unmodified engine); Thief's are loaded
    for path/hint display only -- see ``thief_peer``'s own replay viewer
    for Thief's real verdict. The overall banner reflects Police's own
    verification result only, never a fabricated claim about Thief's."""
    police_side, police_bundle = _own_side(police_dir)
    thief_side, thief_bundle = _opponent_side(thief_dir)
    police_logs = {log.get("sub_game_number"): log for log in police_bundle.logs}
    thief_logs = {log.get("sub_game_number"): log for log in thief_bundle.logs}
    result = police_bundle.result or thief_bundle.result or {}
    sub_games = tuple(
        build_sub_game(entry, police_logs, thief_logs) for entry in result.get("sub_games", [])
    )
    return ReplayViewModel(
        police=police_side,
        thief=thief_side,
        verdict=police_side.verdict,
        verification_ok=police_side.ok,
        declaration=police_bundle.declaration or thief_bundle.declaration,
        config_sha256_prefix=str(result.get("config_sha256", ""))[:8],
        sub_games=sub_games,
    )

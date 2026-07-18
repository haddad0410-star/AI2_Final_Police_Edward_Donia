"""Headless replay/audit verifier (Batch 2, Phase 12).

Loads a whole artifact directory (declaration, configs, logs, result) and
reports ``VERIFIED`` or ``TAMPERED`` with specifics. Verifies game_uid
consistency, config-hash consistency, every commitment/nonce/sequence, barrier
and capture-claim bounds, and score/total consistency. Reads only files -- no
repository-private runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from police_peer.services.replay_checks import scoring_from_terms, verify_log, verify_scores
from police_peer.services.replay_loader import ReplayBundle, load_bundle
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """The verdict of a replay verification plus every specific finding."""

    ok: bool
    findings: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "VERIFIED" if self.ok else "TAMPERED"


def _check_game_uid(bundle: ReplayBundle, findings: list[str]) -> None:
    uids = {d.get("game_uid") for d in bundle.all_dicts()}
    if len(uids) != 1 or None in uids:
        findings.append(f"game_uid not consistent across artifacts: {sorted(map(str, uids))}")


def _check_config_hashes(bundle: ReplayBundle, findings: list[str]) -> None:
    hashes = {c.get("config_sha256") for c in bundle.configs}
    if bundle.result is not None:
        hashes.add(bundle.result.get("config_sha256"))
    if len(hashes) > 1:
        findings.append("config_sha256 differs across config/result artifacts")


def _check_counts(bundle: ReplayBundle, findings: list[str]) -> None:
    n_config, n_log = len(bundle.configs), len(bundle.logs)
    n_result = len(bundle.result["sub_games"]) if bundle.result else 0
    if not (n_config == n_log == n_result) or n_config == 0:
        findings.append(
            f"artifact counts differ: {n_config} configs, {n_log} logs, {n_result} results"
        )


def _check_no_duplicate_sub_games(bundle: ReplayBundle, findings: list[str]) -> None:
    """Two files with different names can still both claim the SAME
    ``sub_game_number`` internally; a naive dict-keyed lookup would silently
    keep only the last one. Reject that outright rather than silently
    dropping a record."""
    for label, items in (("config", bundle.configs), ("log", bundle.logs)):
        numbers = [item.get("sub_game_number") for item in items]
        duplicates = {n for n in numbers if numbers.count(n) > 1}
        if duplicates:
            findings.append(f"duplicate sub_game_number in {label} artifacts: {sorted(duplicates)}")


def _check_step_counts(bundle: ReplayBundle, findings: list[str]) -> None:
    """A log missing a step (declared by the result) means a record was dropped."""
    logs_by_number = {log.get("sub_game_number"): log for log in bundle.logs}
    for entry in bundle.result["sub_games"]:
        log = logs_by_number.get(entry["sub_game_number"])
        if log is not None and len(log["steps"]) != entry["steps"]:
            findings.append(
                f"sub-game {entry['sub_game_number']}: log has {len(log['steps'])} steps, "
                f"result declares {entry['steps']} (a record is missing/added)"
            )


def verify_replay(directory: Path) -> ReplayReport:
    """Verify a full artifact set; return a :class:`ReplayReport`."""
    findings: list[str] = []
    try:
        bundle = load_bundle(directory)
    except (OSError, SchemaValidationError, ValueError) as exc:
        return ReplayReport(False, [f"failed to load artifacts: {exc}"])
    if bundle.result is None or not bundle.configs or not bundle.logs:
        return ReplayReport(False, ["missing required artifacts (config/log/result)"])

    _check_game_uid(bundle, findings)
    _check_config_hashes(bundle, findings)
    _check_counts(bundle, findings)
    _check_no_duplicate_sub_games(bundle, findings)
    _check_step_counts(bundle, findings)

    grid_size = bundle.configs[0]["terms"]["board_and_agents"]["grid_size"]
    for log in bundle.logs:
        findings.extend(verify_log(log, grid_size))
    try:
        scoring = scoring_from_terms(bundle.configs[0]["terms"])
        findings.extend(verify_scores(bundle.result, scoring))
    except (KeyError, TypeError) as exc:
        findings.append(f"score recomputation failed: {exc}")

    return ReplayReport(not findings, findings)

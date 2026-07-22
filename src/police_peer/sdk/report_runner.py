"""Batch 4A Task 9/12, Batch 4B Task 9: assembles a Gmail report from real
artifact files on disk and either dry-runs (default, no network) or sends
(explicit ``--send`` + real credentials, always through the Gatekeeper).

Batch 4B: when an opponent artifacts directory is available, the report
is gated on FULL BILATERAL verification (``services.bilateral_verify`` --
both sides independently verified, both VERIFIED), not merely this side's
own single-sided ``verify_replay``. Without an opponent directory (this
side's local `--artifacts-dir`-only invocation, e.g. before any opponent
artifacts exist), the gate falls back to the single-sided check -- still
strictly more conservative than a bilateral pass, never less.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
from pathlib import Path

from police_peer.domain.gmail_report_schema import build_report
from police_peer.infrastructure.gmail_credentials import (
    CredentialResolutionError,
    resolve_credential_paths,
)
from police_peer.infrastructure.gmail_gatekeeper import Gatekeeper
from police_peer.infrastructure.gmail_sender import build_real_send_fn, dry_run, send
from police_peer.services.bilateral_verify import verify_bilateral
from police_peer.services.replay_verifier import verify_replay
from police_peer.shared.config_loader import load_rate_limits


class ReportRefusedError(Exception):
    """Raised when the underlying artifacts fail bilateral verification --
    a report (dry-run or send) must never be built from an unverified/
    tampered result, since Appendix E requires truthful declarations."""


def _load_bundle(artifacts_dir: Path) -> tuple[dict, dict, list[dict], list[Path]]:
    declaration_paths = sorted(artifacts_dir.glob("declaration_*.json"))
    result_paths = sorted(artifacts_dir.glob("result_*.json"))
    log_paths = sorted(artifacts_dir.glob("log_*.json"))
    if not declaration_paths or not result_paths:
        raise FileNotFoundError(f"missing declaration/result artifacts under {artifacts_dir}")
    declaration = json.loads(declaration_paths[0].read_text())
    result = json.loads(result_paths[0].read_text())
    logs = [json.loads(p.read_text()) for p in log_paths]
    all_paths = [*declaration_paths, *result_paths, *log_paths]
    return declaration, result, logs, all_paths


def _require_verified(artifacts_dir: Path, opponent_artifacts_dir: Path | None) -> None:
    if opponent_artifacts_dir is None:
        verification = verify_replay(artifacts_dir)
        if not verification.ok:
            raise ReportRefusedError(
                f"refusing to build a report from unverified artifacts under {artifacts_dir}: "
                f"{verification.verdict} -- {'; '.join(verification.findings)}"
            )
        return
    own_side, opp_side, full_bilateral = verify_bilateral(artifacts_dir, opponent_artifacts_dir)
    if not full_bilateral:
        raise ReportRefusedError(
            "refusing to build a report: full bilateral verification did not pass -- "
            f"own(independently_verified={own_side.independently_verified}, verdict={own_side.verdict}), "
            f"opponent(independently_verified={opp_side.independently_verified}, verdict={opp_side.verdict})"
        )


def build_report_from_artifacts(
    artifacts_dir: Path, opponent_artifacts_dir: Path | None = None
) -> dict:
    _require_verified(artifacts_dir, opponent_artifacts_dir)
    declaration, result, logs, paths = _load_bundle(artifacts_dir)
    return build_report(declaration=declaration, result=result, artifact_paths=paths, logs=logs)


def run_dry_run(artifacts_dir: Path, opponent_artifacts_dir: Path | None = None) -> dict:
    report = build_report_from_artifacts(artifacts_dir, opponent_artifacts_dir)
    plan = dry_run(report)
    return dataclasses.asdict(plan)


def run_send(
    artifacts_dir: Path, rate_limits_path: Path, opponent_artifacts_dir: Path | None = None
) -> dict:
    """Real send path -- requires real credentials AND an explicit caller
    decision; never reached unless ``--send`` is passed on the CLI."""
    report = build_report_from_artifacts(artifacts_dir, opponent_artifacts_dir)
    try:
        credentials = resolve_credential_paths()
    except CredentialResolutionError as exc:
        return {"ok": False, "error": str(exc)}
    config = load_rate_limits(rate_limits_path)
    send_fn = build_real_send_fn(credentials)()
    gatekeeper = Gatekeeper(config, send_fn)
    result = asyncio.run(
        send(report, gatekeeper, credentials, ["https://www.googleapis.com/auth/gmail.send"])
    )
    return dataclasses.asdict(result)

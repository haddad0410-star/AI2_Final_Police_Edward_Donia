"""CLI entry point.

Commands:
- ``negotiate-smoke``   : Batch 1 minimal real FastMCP negotiation slice.
- ``run-subgame``       : run one sub-game against a live opponent (Phase 9).
- ``run-series``        : run the full 6-game series (``--smoke`` = 1 game) (Phase 10).
- ``verify-replay``     : headless artifact verifier, VERIFIED/TAMPERED (Phase 12).
- ``peer``              : run a series with ``--gui``/``--no-gui`` (Batch 4A).
- ``replay``            : graphical/headless post-game replay viewer (Batch 4A).
- ``report``            : Gmail dry-run report (``--send`` for a real send; Batch 4A).

Business logic lives in the SDK/services layers; this file only parses args and
routes to them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from police_peer import cli_gmail, cli_runners
from police_peer.domain.roles import Role
from police_peer.sdk.negotiation_runner import run_negotiation_smoke
from police_peer.services.replay_verifier import verify_replay

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"


def _negotiate_smoke(args: argparse.Namespace) -> int:
    config_dir = Path(args.config_dir) if args.config_dir else CONFIG_DIR
    summary = asyncio.run(run_negotiation_smoke(Role.POLICE, config_dir))
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("outcome") == "negotiated" else 1


def _verify_replay(args: argparse.Namespace) -> int:
    report = verify_replay(Path(args.artifacts))
    print(report.verdict)
    for finding in report.findings:
        print(f"  - {finding}")
    return 0 if report.ok else 2


def _replay(args: argparse.Namespace) -> int:
    from police_peer.gui.replay_view_model import build_replay_view

    police_dir, thief_dir = Path(args.police_artifacts), Path(args.thief_artifacts)
    if not args.gui:
        model = build_replay_view(police_dir, thief_dir)
        print(f"REPLAY VERDICT: {model.verdict}")
        print(f"FULL_BILATERAL_VERIFICATION={str(model.full_bilateral_verification).lower()}")
        print(
            f"police: independently_verified={model.police.independently_verified} verdict={model.police.verdict}"
        )
        print(
            f"thief: independently_verified={model.thief.independently_verified} verdict={model.thief.verdict}"
        )
        for f in (*model.police.findings, *model.thief.findings):
            print(f"  - {f}")
        return 0 if model.verification_ok else 2
    from police_peer.gui.tk_replay_app import ReplayApp

    app = ReplayApp(police_dir, thief_dir)
    ok = app.model.verification_ok
    app.run()
    return 0 if ok else 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="police_peer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    negotiate = subparsers.add_parser(
        "negotiate-smoke", help="Batch 1 minimal FastMCP negotiation slice"
    )
    negotiate.add_argument(
        "--config-dir", default=None, help="override the default config/police directory"
    )

    default_url = "http://127.0.0.1:8902/mcp"
    public_help = (
        "Gate A1: enforce Authorization: Bearer PUBLIC_BIND_TOKEN on every "
        "incoming request (still binds 127.0.0.1 only). Requires a nonempty "
        "PUBLIC_BIND_TOKEN env var; OPPONENT_MCP_TOKEN is used when calling out."
    )
    sub = subparsers.add_parser("run-subgame", help="Run one sub-game vs a live opponent")
    sub.add_argument("--headless", action="store_true", help="headless (no GUI); default mode")
    sub.add_argument("--config-dir", default=str(CONFIG_DIR))
    sub.add_argument("--opponent-url", default=default_url)
    sub.add_argument("--public", action="store_true", help=public_help)

    series = subparsers.add_parser("run-series", help="Run the full 6-game series")
    series.add_argument("--headless", action="store_true", help="headless (no GUI); default mode")
    series.add_argument("--smoke", action="store_true", help="single-game SMOKE TEST ONLY")
    series.add_argument("--config-dir", default=str(CONFIG_DIR))
    series.add_argument("--opponent-url", default=default_url)
    series.add_argument(
        "--artifacts-dir", default=None, help="write the 4 standardized JSON artifacts here"
    )
    series.add_argument("--public", action="store_true", help=public_help)

    verify = subparsers.add_parser("verify-replay", help="Verify an artifact directory")
    verify.add_argument("--artifacts", required=True, help="directory of JSON artifacts")

    peer = subparsers.add_parser("peer", help="Run a series with a live GUI (Batch 4A)")
    gui_group = peer.add_mutually_exclusive_group()
    gui_group.add_argument("--gui", action="store_true", help="launch the live Tkinter view")
    gui_group.add_argument("--no-gui", action="store_true", help="headless (default)")
    peer.add_argument("--smoke", action="store_true", help="single-game SMOKE TEST ONLY")
    peer.add_argument("--config-dir", default=str(CONFIG_DIR))
    peer.add_argument("--opponent-url", default=default_url)
    peer.add_argument("--artifacts-dir", default=None)
    peer.add_argument("--public", action="store_true", help=public_help)

    replay = subparsers.add_parser("replay", help="Graphical/headless post-game replay viewer")
    replay.add_argument("--gui", action="store_true", help="launch the graphical replay viewer")
    replay.add_argument("--police-artifacts", required=True)
    replay.add_argument("--thief-artifacts", required=True)

    report = subparsers.add_parser("report", help="Gmail report (dry-run by default)")
    report.add_argument("--artifacts-dir", required=True)
    report.add_argument(
        "--opponent-artifacts-dir",
        default=None,
        help="opponent's artifacts dir -- gates the report on full bilateral verification (Batch 4B)",
    )
    report.add_argument("--send", action="store_true", help="real send (requires credentials)")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "negotiate-smoke":
        sys.exit(_negotiate_smoke(args))
    if args.command == "run-subgame":
        sys.exit(cli_runners.run_subgame(args))
    if args.command == "run-series":
        sys.exit(cli_runners.run_series(args))
    if args.command == "verify-replay":
        sys.exit(_verify_replay(args))
    if args.command == "peer":
        sys.exit(cli_runners.run_peer(args))
    if args.command == "replay":
        sys.exit(_replay(args))
    if args.command == "report":
        sys.exit(cli_gmail.report(args))
    raise NotImplementedError(f"command {args.command!r} is not implemented yet")


if __name__ == "__main__":
    main()

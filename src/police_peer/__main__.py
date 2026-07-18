"""CLI entry point.

Commands:
- ``negotiate-smoke``   : Batch 1 minimal real FastMCP negotiation slice.
- ``run-subgame``       : run one sub-game against a live opponent (Phase 9).
- ``run-series``        : run the full 6-game series (``--smoke`` = 1 game) (Phase 10).
- ``verify-replay``     : headless artifact verifier, VERIFIED/TAMPERED (Phase 12).

Business logic lives in the SDK/services layers; this file only parses args and
routes to them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.sdk.game_runner import (
    print_summary,
    run_series_headless,
    run_subgame_headless,
    summary_exit_code,
)
from police_peer.sdk.negotiation_runner import run_negotiation_smoke
from police_peer.services.replay_verifier import verify_replay

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"


def _negotiate_smoke(args: argparse.Namespace) -> int:
    config_dir = Path(args.config_dir) if args.config_dir else CONFIG_DIR
    summary = asyncio.run(run_negotiation_smoke(Role.POLICE, config_dir))
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("outcome") == "negotiated" else 1


def _run_subgame(args: argparse.Namespace) -> int:
    summary = asyncio.run(run_subgame_headless(Path(args.config_dir), args.opponent_url))
    print_summary(summary)
    return summary_exit_code(summary)


def _run_series(args: argparse.Namespace) -> int:
    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else None
    summary = asyncio.run(
        run_series_headless(
            Path(args.config_dir), args.opponent_url, smoke=args.smoke, artifacts_dir=artifacts_dir
        )
    )
    print_summary(summary)
    return summary_exit_code(summary)


def _verify_replay(args: argparse.Namespace) -> int:
    report = verify_replay(Path(args.artifacts))
    print(report.verdict)
    for finding in report.findings:
        print(f"  - {finding}")
    return 0 if report.ok else 2


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
    sub = subparsers.add_parser("run-subgame", help="Run one sub-game vs a live opponent")
    sub.add_argument("--headless", action="store_true", help="headless (no GUI); default mode")
    sub.add_argument("--config-dir", default=str(CONFIG_DIR))
    sub.add_argument("--opponent-url", default=default_url)

    series = subparsers.add_parser("run-series", help="Run the full 6-game series")
    series.add_argument("--headless", action="store_true", help="headless (no GUI); default mode")
    series.add_argument("--smoke", action="store_true", help="single-game SMOKE TEST ONLY")
    series.add_argument("--config-dir", default=str(CONFIG_DIR))
    series.add_argument("--opponent-url", default=default_url)
    series.add_argument(
        "--artifacts-dir", default=None, help="write the 4 standardized JSON artifacts here"
    )

    verify = subparsers.add_parser("verify-replay", help="Verify an artifact directory")
    verify.add_argument("--artifacts", required=True, help="directory of JSON artifacts")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "negotiate-smoke":
        sys.exit(_negotiate_smoke(args))
    if args.command == "run-subgame":
        sys.exit(_run_subgame(args))
    if args.command == "run-series":
        sys.exit(_run_series(args))
    if args.command == "verify-replay":
        sys.exit(_verify_replay(args))
    raise NotImplementedError(f"command {args.command!r} is not implemented yet")


if __name__ == "__main__":
    main()

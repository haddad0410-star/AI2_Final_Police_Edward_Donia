"""CLI entry point.

Batch 1 implements only `negotiate-smoke`: the minimal real FastMCP vertical
slice (health/negotiate/config-hash-compare/ack/clean-shutdown). The full
`peer`/`replay` game commands are a later batch -- see docs/TODO.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.sdk.negotiation_runner import run_negotiation_smoke

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"


def _negotiate_smoke() -> int:
    summary = asyncio.run(run_negotiation_smoke(Role.POLICE, CONFIG_DIR))
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("outcome") == "negotiated" else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="police_peer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "negotiate-smoke", help="Run the Batch 1 minimal real FastMCP negotiation slice"
    )
    args = parser.parse_args()

    if args.command == "negotiate-smoke":
        sys.exit(_negotiate_smoke())
    raise NotImplementedError(f"command {args.command!r} is not implemented yet")


if __name__ == "__main__":
    main()

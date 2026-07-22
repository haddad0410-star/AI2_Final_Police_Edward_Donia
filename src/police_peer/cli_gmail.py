"""Batch 4A Task 9/12: ``report`` CLI handler, split out of ``__main__.py``
to keep it under the 150-meaningful-line cap. Argument-parsing/dispatch
only -- no business logic lives here either.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from police_peer.sdk.report_runner import ReportRefusedError, run_dry_run, run_send

RATE_LIMITS_PATH = Path(__file__).resolve().parents[2] / "config" / "police" / "rate_limits.json"


def report(args: argparse.Namespace) -> int:
    artifacts_dir = Path(args.artifacts_dir)
    try:
        if not args.send:
            result = run_dry_run(artifacts_dir)
            print(json.dumps(result, indent=2))
            return 0
        result = run_send(artifacts_dir, RATE_LIMITS_PATH)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    except ReportRefusedError as exc:
        print(json.dumps({"ok": False, "refused": True, "reason": str(exc)}, indent=2))
        return 3

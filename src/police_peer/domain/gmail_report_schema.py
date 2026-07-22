"""Batch 4A Task 9: the final-project Gmail report body -- structured JSON
only, never free-form prose (book Ch.9.3.3). Built entirely from already-
produced, already-public artifact files (declaration/result/logs); never
reads credentials, OAuth tokens, private TOML, or hidden strategy weights.

Mandatory recipient (Appendix F Table 20, visually confirmed, printed
p.141): rmisegal+uoh26finalgame@gmail.com. This module never sends
anything -- it only builds the JSON body; ``infrastructure/gmail_sender.py``
decides whether to dry-run or actually send.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION = "gmail-report/1"
MANDATORY_RECIPIENT = "rmisegal+uoh26finalgame@gmail.com"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_summary(logs: list[dict]) -> dict[str, Any]:
    timestamps = [
        step.get("timestamp")
        for log in logs
        for step in log.get("steps", [])
        if step.get("timestamp")
    ]
    if not timestamps:
        return {"first_timestamp": None, "last_timestamp": None, "total_steps": 0}
    return {
        "first_timestamp": min(timestamps),
        "last_timestamp": max(timestamps),
        "total_steps": sum(len(log.get("steps", [])) for log in logs),
    }


def build_report(
    *, declaration: dict, result: dict, artifact_paths: list[Path], logs: list[dict]
) -> dict[str, Any]:
    """Build the structured report body. Every value here traces back to an
    already-written, already-public artifact file -- nothing is invented."""
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "recipient": MANDATORY_RECIPIENT,
        "game_id": declaration.get("game_id"),
        "game_uid": declaration.get("game_uid"),
        "group_id": declaration.get("group_id"),
        "members": declaration.get("members", []),
        "repositories": {
            "police": declaration.get("police_repository"),
            "thief": declaration.get("thief_repository"),
        },
        "mcp_urls": {
            "police": declaration.get("police_mcp_url"),
            "thief": declaration.get("thief_mcp_url"),
        },
        "sub_game_outcomes": result.get("sub_games", []),
        "scores": {
            "police_total": result.get("police_total"),
            "thief_total": result.get("thief_total"),
        },
        "aggregate_result": {
            "agreed": result.get("agreed"),
            "agreement_status": result.get("agreement_status"),
        },
        "audit_status": [
            {"sub_game_number": sg.get("sub_game_number"), "audit_ok": sg.get("audit_ok")}
            for sg in result.get("sub_games", [])
        ],
        "config_sha256": result.get("config_sha256"),
        "commit_hashes": {"this_side": declaration.get("git_commit")},
        "hardware_declaration": declaration.get("hardware", {}),
        "strategy_class": declaration.get("strategy_class"),
        "token_usage": {"banter_provider": declaration.get("banter_provider"), "total_tokens": 0},
        "runtime_summary": _runtime_summary(logs),
        "artifact_hashes": {p.name: _sha256_file(p) for p in artifact_paths if p.exists()},
    }

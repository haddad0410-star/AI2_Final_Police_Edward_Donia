"""Real-HTTP coverage for the headless runner + HttpOpponentTransport.

Runs run_subgame_headless against a bare local opponent server that accepts our
calls but never sends a reveal back, so the transport's bounded poll budget is
exhausted and the sub-game ends as a clean, explicit TECHNICAL_LOSS (never a
hang). This exercises the real client->server round-trip without needing a full
second peer implementation.

Both this peer's own server and the opponent's stand-in server bind a
dynamically allocated free localhost port per test run (see ``_port_utils``),
never a hardcoded one -- see the module docstring there for why.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from _port_utils import (
    HOST,
    free_tcp_port,
    isolated_police_config_dir,
    start_test_server,
    stop_test_server,
)

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.sdk.game_runner import run_series_headless, summary_exit_code
from police_peer.sdk.subgame_runner import run_subgame_headless
from police_peer.shared.config_loader import sha256_hex

REAL_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"


def test_run_subgame_headless_against_silent_opponent(tmp_path: Path) -> None:
    async def scenario() -> None:
        opponent_port = free_tcp_port()
        my_port = free_tcp_port()
        config_dir = isolated_police_config_dir(
            REAL_CONFIG_DIR, tmp_path / "config", my_port=my_port, opponent_port=opponent_port
        )
        config_sha = sha256_hex(config_dir / "game.json")
        mcp, _ = build_peer_server(Role.THIEF, config_sha, game_uid="uid")
        opp_server = await start_test_server(mcp, opponent_port)
        try:
            summary = await run_subgame_headless(
                config_dir,
                f"http://{HOST}:{opponent_port}/mcp",
                poll_interval=0.01,
                max_polls=2,  # exhaust quickly -> technical loss, no real waiting
            )
        finally:
            await stop_test_server(opp_server)
        assert summary["mode"] == "run-subgame"
        assert summary["result"] == "technical_loss"
        assert summary["final_state"] == "error"
        assert summary_exit_code(summary) == 1

    asyncio.run(scenario())


def test_run_series_headless_smoke_against_silent_opponent(tmp_path: Path) -> None:
    async def scenario() -> None:
        opponent_port = free_tcp_port()
        my_port = free_tcp_port()
        config_dir = isolated_police_config_dir(
            REAL_CONFIG_DIR, tmp_path / "config", my_port=my_port, opponent_port=opponent_port
        )
        config_sha = sha256_hex(config_dir / "game.json")
        mcp, _ = build_peer_server(Role.THIEF, config_sha, game_uid="uid")
        opp_server = await start_test_server(mcp, opponent_port)
        try:
            summary = await run_series_headless(
                config_dir,
                f"http://{HOST}:{opponent_port}/mcp",
                smoke=True,
                poll_interval=0.01,
                max_polls=2,
            )
        finally:
            await stop_test_server(opp_server)
        assert summary["mode"] == "run-series"
        # The silent opponent yields a technical loss, ending the series immediately.
        assert summary["terminated_reason"] == "technical_loss_ended_series"
        assert summary_exit_code(summary) == 1

    asyncio.run(scenario())


def test_run_series_headless_writes_artifacts_when_requested(tmp_path: Path) -> None:
    """Regression: artifact generation (Phase 11) existed and was unit-tested
    in isolation, but nothing ever called it from the actual run-series
    execution path -- found during the session-recovery-step-B Phase 10-12
    audit. This proves a real (albeit technical-loss-shortened) series run
    now genuinely writes all 4 standardized artifacts, sharing one game_uid.
    """
    artifacts_dir = tmp_path / "artifacts"

    async def scenario() -> dict:
        opponent_port = free_tcp_port()
        my_port = free_tcp_port()
        config_dir = isolated_police_config_dir(
            REAL_CONFIG_DIR, tmp_path / "config", my_port=my_port, opponent_port=opponent_port
        )
        config_sha = sha256_hex(config_dir / "game.json")
        mcp, _ = build_peer_server(Role.THIEF, config_sha, game_uid="uid")
        opp_server = await start_test_server(mcp, opponent_port)
        try:
            return await run_series_headless(
                config_dir,
                f"http://{HOST}:{opponent_port}/mcp",
                smoke=True,
                poll_interval=0.01,
                max_polls=2,
                artifacts_dir=artifacts_dir,
            )
        finally:
            await stop_test_server(opp_server)

    summary = asyncio.run(scenario())
    written = summary["artifacts_written"]
    assert len(written) == 4  # declaration + (config, log) x1 smoke game + result
    game_id = summary["game_id"]
    paths = [
        artifacts_dir / f"declaration_{game_id}.json",
        artifacts_dir / f"config_{game_id}_g01.json",
        artifacts_dir / f"log_{game_id}_g01.json",
        artifacts_dir / f"result_{game_id}.json",
    ]
    for path in paths:
        assert path.exists(), path

    uids = {json.loads(path.read_text())["game_uid"] for path in paths}
    assert uids == {summary["game_uid"]}

"""Coverage for sdk.negotiation_runner.run_negotiation_smoke, exercised
directly (not via a real OS subprocess -- that's what
integration_lab/run_negotiation_smoke.py is for) so pytest can measure it."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_server import build_peer_server, run_server_until_cancelled
from police_peer.sdk.negotiation_runner import run_negotiation_smoke

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _write_config(tmp_path: Path, my_port: int, opponent_port: int) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "game.json").write_bytes((FIXTURES / "valid_shared_game.json").read_bytes())
    toml = f"""
version = "0.1.0"
[game]
group_name = "Edward-Donia"
group_id = "edward-donia"
sub_game_number = 1
members = ["Edward Haddad 214083115"]
[network]
my_port = {my_port}
opponent_url = "http://127.0.0.1:{opponent_port}/mcp"
turn_timeout_seconds = 5
"""
    (config_dir / "game.toml").write_text(toml)
    return config_dir


def test_run_negotiation_smoke_succeeds_against_a_real_fake_opponent(tmp_path) -> None:
    async def scenario() -> None:
        opponent_port = 18801
        # A stand-in opponent server, using this SAME package's own server
        # builder -- exercises the client side of negotiation_runner without
        # importing the sibling repo.
        config_dir = _write_config(tmp_path, my_port=18800, opponent_port=opponent_port)
        opponent_hash = hashlib.sha256((config_dir / "game.json").read_bytes()).hexdigest()
        mcp, _ = build_peer_server(Role.THIEF, opponent_hash)
        opponent_task = asyncio.create_task(
            run_server_until_cancelled(mcp, "127.0.0.1", opponent_port)
        )
        await asyncio.sleep(0.3)
        try:
            summary = await run_negotiation_smoke(
                Role.POLICE,
                config_dir,
                startup_grace_seconds=0.2,
                health_attempts=5,
                health_delay_seconds=0.2,
                post_negotiation_linger_seconds=0.1,
            )
            assert summary["outcome"] == "negotiated"
            assert summary["config_ack"]["accepted"] is True
        finally:
            opponent_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await opponent_task

    asyncio.run(scenario())


def test_run_negotiation_smoke_reports_unavailable_opponent(tmp_path) -> None:
    async def scenario() -> None:
        config_dir = _write_config(tmp_path, my_port=18802, opponent_port=18999)
        summary = await run_negotiation_smoke(
            Role.POLICE,
            config_dir,
            startup_grace_seconds=0.1,
            health_attempts=2,
            health_delay_seconds=0.1,
            post_negotiation_linger_seconds=0.0,
        )
        assert summary["outcome"] == "opponent_unavailable"

    asyncio.run(scenario())

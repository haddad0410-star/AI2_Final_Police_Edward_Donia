"""SDK-level orchestration for this batch's minimal negotiation vertical slice.

Ties together: config loading, starting this peer's own FastMCP server, and
calling the opponent's server as a client -- exactly the subset needed for
health/negotiate/config-hash-compare/ack/clean-shutdown. The full game loop
(turn commit/reveal, audit) is implemented separately in `sdk/game_runner.py`,
not by this module.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.infrastructure.mcp_client import (
    PeerUnavailableError,
    call_negotiate,
    call_propose_config,
    wait_for_health,
)
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.server_lifecycle import ManagedServer
from police_peer.shared.config_loader import load_private_config, load_shared_config, sha256_hex


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def run_negotiation_smoke(
    role: Role,
    config_dir: Path,
    shared_config_filename: str = "game.json",
    private_config_filename: str = "game.toml",
    startup_grace_seconds: float = 0.4,
    health_attempts: int = 15,
    health_delay_seconds: float = 0.3,
    post_negotiation_linger_seconds: float = 5.0,
) -> dict:
    """Run this peer's side of the negotiation smoke test; returns a JSON-safe
    summary dict (never raises for an expected opponent-unavailable outcome --
    that outcome is reported in the summary instead).

    `post_negotiation_linger_seconds`: this peer keeps its OWN server running
    for a grace period after completing ITS OWN negotiation attempt, so a
    slower-starting opponent (e.g. due to `uv run` startup skew between two
    independent processes) still has time to reach US before we shut down --
    otherwise a peer that finishes first can tear down before the other side's
    retry loop ever succeeds, even though both sides behaved correctly."""
    shared = load_shared_config(config_dir / shared_config_filename)
    private = load_private_config(config_dir / private_config_filename)
    own_config_sha256 = sha256_hex(config_dir / shared_config_filename)

    mcp, inbox = build_peer_server(role, own_config_sha256)
    server = ManagedServer(mcp, "127.0.0.1", private.network.my_port)
    await server.start()
    await asyncio.sleep(startup_grace_seconds)

    summary: dict = {
        "role": role.value,
        "my_port": private.network.my_port,
        "opponent_url": private.network.opponent_url,
        "own_config_sha256": own_config_sha256,
        "group_id": private.game.group_id,
        "started_at": _now_iso(),
    }
    try:
        await wait_for_health(private.network.opponent_url, health_attempts, health_delay_seconds)
        summary["opponent_health"] = "ok"

        declaration = {
            "envelope": {"correlation_id": f"{private.game.group_id}-declare"},
            "group_id": private.game.group_id,
            "group_name": private.game.group_name,
            "mcp_url": f"http://127.0.0.1:{private.network.my_port}/mcp",
        }
        negotiate_result = await call_negotiate(private.network.opponent_url, declaration)
        summary["negotiate_result"] = negotiate_result

        proposal = {
            "envelope": {"correlation_id": f"{private.game.group_id}-config"},
            "config_sha256": own_config_sha256,
        }
        ack = await call_propose_config(private.network.opponent_url, proposal)
        summary["config_ack"] = ack
        summary["shared_config_num_games"] = shared.network_and_league.num_games
        summary["outcome"] = "negotiated" if ack.get("accepted") else "config_mismatch"
    except PeerUnavailableError as exc:
        summary["opponent_health"] = "unavailable"
        summary["outcome"] = "opponent_unavailable"
        summary["error"] = str(exc)
    finally:
        await asyncio.sleep(post_negotiation_linger_seconds)
        summary["received_declarations"] = inbox.declarations.qsize()
        summary["received_proposals"] = inbox.proposals.qsize()
        shutdown = await server.stop()
        summary["shutdown_outcome"] = shutdown.outcome.value
        summary["ended_at"] = _now_iso()

    return summary

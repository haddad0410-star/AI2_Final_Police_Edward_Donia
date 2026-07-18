"""SDK orchestration for the headless game CLIs (Batch 2, Phases 9-11).

Wires config loading, this peer's own FastMCP server, the HTTP opponent
transport, the sub-game/series runtimes, and artifact writing into two async
entrypoints. Business logic lives here (not in ``__main__``) per CLAUDE.md.

The live cross-process path was validated for real in session recovery step C
(Task 5): two independent OS processes, real HTTP, real commit-reveal, ending
in a genuine capture/survival/technical-loss outcome -- see
integration_lab/evidence/session_recovery_step_c/one_subgame/. The runtimes
it drives are also covered by tests against in-process fakes.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerStateMachine
from police_peer.infrastructure.http_transport import HttpOpponentTransport
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.server_lifecycle import ManagedServer
from police_peer.services.game_ids import derive_game_id, derive_game_uid
from police_peer.services.series_artifacts import write_series_artifacts
from police_peer.services.series_runtime import run_series
from police_peer.services.subgame_runtime import run_single_subgame
from police_peer.shared.config_loader import load_private_config, load_shared_config, sha256_hex


def _load(config_dir: Path):
    shared = load_shared_config(config_dir / "game.json")
    private = load_private_config(config_dir / "game.toml")
    config_sha = sha256_hex(config_dir / "game.json")
    group_ids = shared.agreed_between
    game_id = derive_game_id(group_ids)
    game_uid = derive_game_uid(config_sha, group_ids)
    return shared, private, config_sha, game_id, game_uid


async def _serve(role: Role, config_sha: str, game_uid: str, machine: PeerStateMachine, port: int):
    mcp, inbox = build_peer_server(role, config_sha, game_uid=game_uid, machine=machine)
    server = ManagedServer(mcp, "127.0.0.1", port)
    await server.start()
    return server, inbox


async def run_subgame_headless(
    config_dir: Path,
    opponent_url: str,
    *,
    poll_interval: float = 0.1,
    max_polls: int = 300,
) -> dict:
    """Run one sub-game against a live opponent server; return a JSON-safe summary."""
    shared, private, config_sha, game_id, game_uid = _load(config_dir)
    machine = PeerStateMachine()
    server, inbox = await _serve(
        Role.POLICE, config_sha, game_uid, machine, private.network.my_port
    )
    transport = HttpOpponentTransport(
        opponent_url,
        inbox,
        grid_size=shared.board_and_agents.grid_size,
        poll_interval=poll_interval,
        max_polls=max_polls,
    )
    try:
        result = await run_single_subgame(
            shared, private, transport, game_uid=game_uid, config_sha256=config_sha, machine=machine
        )
    finally:
        await server.stop()
    return {
        "mode": "run-subgame",
        "game_id": game_id,
        "game_uid": game_uid,
        "result": result.result.value,
        "steps": result.steps,
        "reason": result.reason,
        "final_state": machine.state.value,
    }


async def run_series_headless(
    config_dir: Path,
    opponent_url: str,
    smoke: bool,
    *,
    poll_interval: float = 0.1,
    max_polls: int = 300,
    artifacts_dir: Path | None = None,
) -> dict:
    """Run a full (or --smoke single) series against a live opponent server.

    When `artifacts_dir` is given, writes the four standardized JSON
    artifacts (declaration, one config + log per sub-game actually played,
    result) via `series_artifacts.write_series_artifacts` -- reflecting
    exactly what happened, including a series that ended early on a
    technical loss.
    """
    shared, private, config_sha, game_id, game_uid = _load(config_dir)
    num_games = 1 if smoke else None
    if smoke:
        print("SMOKE TEST ONLY: running a single sub-game, not the full 6-game series.")
    machine = PeerStateMachine()
    server, inbox = await _serve(
        Role.POLICE, config_sha, game_uid, machine, private.network.my_port
    )

    def provider(_index: int) -> HttpOpponentTransport:
        return HttpOpponentTransport(
            opponent_url,
            inbox,
            grid_size=shared.board_and_agents.grid_size,
            poll_interval=poll_interval,
            max_polls=max_polls,
        )

    try:
        series = await run_series(
            shared,
            private,
            provider,
            game_uid=game_uid,
            config_sha256=config_sha,
            num_games=num_games,
            machine=machine,
        )
    finally:
        await server.stop()
    written_artifacts: list[str] = []
    if artifacts_dir is not None:
        paths = write_series_artifacts(
            artifacts_dir, config_dir, private, game_id, game_uid, config_sha, series
        )
        written_artifacts = [str(p) for p in paths]
    return {
        "mode": "run-series",
        "game_id": game_id,
        "game_uid": game_uid,
        "sub_games_played": len(series.sub_games),
        "agreement_status": series.agreement.status,
        "police_total": series.agreement.police_total,
        "thief_total": series.agreement.thief_total,
        "terminated_reason": series.terminated_reason,
        "final_state": series.final_state.value,
        "artifacts_written": written_artifacts,
    }


def summary_exit_code(summary: dict) -> int:
    """0 for a clean finish, 1 for a technical loss / dispute."""
    if summary.get("result") == SubGameResult.TECHNICAL_LOSS.value:
        return 1
    if summary.get("terminated_reason", "completed") != "completed":
        return 1
    return 0


def print_summary(summary: dict) -> None:
    print(json.dumps(summary, indent=2))

"""SDK orchestration for the headless game CLIs. Wires config loading, this
peer's own FastMCP server, the HTTP opponent transport, the sub-game/series
runtimes, the end-of-series bilateral result agreement, and artifact writing
into two async entrypoints. Business logic lives here, not in ``__main__``,
per CLAUDE.md. Validated over real, independent, two-process HTTP runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerStateMachine
from police_peer.infrastructure.http_transport import HttpOpponentTransport
from police_peer.infrastructure.mcp_server import build_peer_server
from police_peer.infrastructure.outbound_pacer import OutboundPacer
from police_peer.infrastructure.server_lifecycle import ManagedServer
from police_peer.sdk.public_mode import build_public_middleware
from police_peer.services.game_ids import derive_game_id, derive_game_uid
from police_peer.services.result_agreement import finalize_series_agreement
from police_peer.services.series_artifacts import write_series_artifacts
from police_peer.services.series_runtime import run_series
from police_peer.shared.config_loader import (
    load_private_config,
    load_rate_limits,
    load_shared_config,
    sha256_hex,
)


def _load(config_dir: Path):
    shared = load_shared_config(config_dir / "game.json")
    private = load_private_config(config_dir / "game.toml")
    config_sha = sha256_hex(config_dir / "game.json")
    group_ids = shared.agreed_between
    game_id = derive_game_id(group_ids)
    game_uid = derive_game_uid(config_sha, group_ids)
    return shared, private, config_sha, game_id, game_uid


async def _serve(
    role: Role,
    config_sha: str,
    game_uid: str,
    machine: PeerStateMachine,
    port: int,
    *,
    public_token: str | None = None,
    config_dir: Path | None = None,
):
    mcp, inbox = build_peer_server(role, config_sha, game_uid=game_uid, machine=machine)
    middleware = build_public_middleware(mcp, public_token, config_dir) if public_token else None
    server = ManagedServer(mcp, "127.0.0.1", port, middleware=middleware)
    await server.start()
    return server, inbox


def _build_pacer(opponent_token: str | None, config_dir: Path) -> OutboundPacer | None:
    """A pacer is only needed when calling a ``--public`` opponent (signaled
    by possessing their token) -- ordinary local self-play never constructs
    one, so its behavior is provably unaffected."""
    if opponent_token is None:
        return None
    return OutboundPacer(load_rate_limits(config_dir / "rate_limits.json"))


async def run_series_headless(
    config_dir: Path,
    opponent_url: str,
    smoke: bool,
    *,
    poll_interval: float = 0.1,
    max_polls: int = 300,
    artifacts_dir: Path | None = None,
    public_token: str | None = None,
    opponent_token: str | None = None,
) -> dict:
    # `artifacts_dir`, if given, gets the four standardized JSON artifacts
    # (declaration, one config+log per sub-game played, result) reflecting
    # exactly what happened, including an early technical-loss ending.
    shared, private, config_sha, game_id, game_uid = _load(config_dir)
    num_games = 1 if smoke else None
    if smoke:
        print("SMOKE TEST ONLY: running a single sub-game, not the full 6-game series.")
    machine = PeerStateMachine()
    server, inbox = await _serve(
        Role.POLICE,
        config_sha,
        game_uid,
        machine,
        private.network.my_port,
        public_token=public_token,
        config_dir=config_dir,
    )
    # One pacer for the WHOLE series (not per sub-game): its sliding window
    # must track cumulative outbound volume across all 6 sub-games, matching
    # the opponent's own incoming Gatekeeper's per-process (not per-sub-game)
    # lifetime.
    pacer = _build_pacer(opponent_token, config_dir)

    def provider(_index: int) -> HttpOpponentTransport:
        return HttpOpponentTransport(
            opponent_url,
            inbox,
            grid_size=shared.board_and_agents.grid_size,
            poll_interval=poll_interval,
            max_polls=max_polls,
            opponent_token=opponent_token,
            pacer=pacer,
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
            opponent_url=opponent_url,
            opponent_token=opponent_token,
        )
        series = await finalize_series_agreement(
            series,
            opponent_url=opponent_url,
            inbox=inbox,
            game_uid=game_uid,
            config_sha256=config_sha,
            role=Role.POLICE,
            opponent_token=opponent_token,
            pacer=pacer,
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
        "agreed": series.agreement.agreed,
        "agreement_status": series.agreement.status,
        "police_total": series.agreement.police_total,
        "thief_total": series.agreement.thief_total,
        "terminated_reason": series.terminated_reason,
        "final_state": series.final_state.value,
        "artifacts_written": written_artifacts,
    }


def summary_exit_code(summary: dict) -> int:
    """0 = clean, agreed finish; 1 = technical loss / incomplete / disputed."""
    if summary.get("result") == SubGameResult.TECHNICAL_LOSS.value:
        return 1
    if summary.get("terminated_reason", "completed") != "completed":
        return 1
    disputed = summary.get("agreement_status") in ("disputed_zeroed", "unverified_self_play")
    return 1 if disputed or summary.get("agreed") is False else 0


def print_summary(summary: dict) -> None:
    print(json.dumps(summary, indent=2))

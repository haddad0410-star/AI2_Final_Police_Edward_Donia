"""``run-subgame`` (single sub-game) entrypoint. Split out of
``game_runner.py`` (Gate A1: `public_token`/`opponent_token` plumbing pushed
that file over the 150-line cap) -- shares `_load`/`_serve` from there
rather than duplicating them.
"""

from __future__ import annotations

from pathlib import Path

from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerStateMachine
from police_peer.infrastructure.http_transport import HttpOpponentTransport
from police_peer.sdk.game_runner import _build_pacer, _load, _serve
from police_peer.services.subgame_runtime import run_single_subgame


async def run_subgame_headless(
    config_dir: Path,
    opponent_url: str,
    *,
    poll_interval: float = 0.1,
    max_polls: int = 300,
    public_token: str | None = None,
    opponent_token: str | None = None,
) -> dict:
    """Run one sub-game against a live opponent server; return a JSON-safe summary."""
    shared, private, config_sha, game_id, game_uid = _load(config_dir)
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
    transport = HttpOpponentTransport(
        opponent_url,
        inbox,
        grid_size=shared.board_and_agents.grid_size,
        poll_interval=poll_interval,
        max_polls=max_polls,
        opponent_token=opponent_token,
        pacer=_build_pacer(opponent_token, config_dir),
    )
    try:
        result = await run_single_subgame(
            shared,
            private,
            transport,
            game_uid=game_uid,
            config_sha256=config_sha,
            machine=machine,
            opponent_url=opponent_url,
            opponent_token=opponent_token,
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

"""Real FastMCP HTTP server for this peer.

Batch 1 tools (``health``, ``negotiate``, ``propose_config``) are kept as-is.
Batch 2 (Phase 6) adds the game-phase tool surface from
``integration_lab/audit/protocol_contract.md`` section 2: one discriminated,
versioned ``receive_turn`` (plus a ``receive_move`` alias onto the exact same
validation path), ``submit_audit``, and ``receive_control``. Handlers only
validate + enqueue + ack; the turn is processed later by the local runtime.

Idempotency policy: a repeated message with the SAME correlation_id/logical key
and identical payload is idempotently acked; a conflicting payload for the same
key is rejected as a protocol violation.
"""

from __future__ import annotations

from fastmcp import FastMCP

from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerStateMachine
from police_peer.infrastructure.inbox import PeerInbox
from police_peer.infrastructure.turn_validation import TurnRouter


def build_peer_server(
    role: Role,
    own_config_sha256: str,
    *,
    game_uid: str = "local-smoke-uid",
    machine: PeerStateMachine | None = None,
    queue_capacity: int = 100,
) -> tuple[FastMCP, PeerInbox]:
    """A FastMCP app exposing the handshake AND game-phase tool surface.

    ``machine`` lets the caller share this peer's lifecycle state machine so the
    handlers can gate on it; a fresh one is created when omitted.
    """
    inbox = PeerInbox(queue_capacity=queue_capacity)
    state_machine = machine if machine is not None else PeerStateMachine()
    router = TurnRouter(
        inbox=inbox,
        machine=state_machine,
        expected_opponent_role=role.opponent(),
        expected_game_uid=game_uid,
        expected_config_sha256=own_config_sha256,
    )
    mcp: FastMCP = FastMCP(name=f"police-thief-{role.value}")

    @mcp.tool
    def health() -> dict:
        """Health/status check."""
        return {"status": "ok", "role": role.value}

    @mcp.tool
    def negotiate(message: dict) -> dict:
        """Receive the opponent's peer declaration."""
        if "group_id" not in message or "envelope" not in message:
            return {"ok": False, "error_code": "MALFORMED", "reason": "missing group_id/envelope"}
        correlation_id = message.get("envelope", {}).get("correlation_id", "")
        if correlation_id and not inbox.record_or_check_conflict(correlation_id, message):
            return {"ok": False, "error_code": "CONFLICTING_DUPLICATE"}
        inbox.declarations.put(message)
        return {"ok": True}

    @mcp.tool
    def propose_config(message: dict) -> dict:
        """Receive the opponent's shared-config hash and compare to our own."""
        if "config_sha256" not in message or "envelope" not in message:
            return {
                "accepted": False,
                "config_sha256_match": False,
                "reason": "malformed message: missing config_sha256/envelope",
            }
        correlation_id = message.get("envelope", {}).get("correlation_id", "")
        if correlation_id and not inbox.record_or_check_conflict(correlation_id, message):
            return {
                "accepted": False,
                "config_sha256_match": False,
                "reason": "conflicting duplicate for this correlation_id",
            }
        inbox.proposals.put(message)
        their_hash = message.get("config_sha256")
        match = their_hash == own_config_sha256
        return {
            "accepted": bool(match),
            "config_sha256_match": bool(match),
            "reason": None if match else "config_sha256 mismatch",
        }

    @mcp.tool
    def receive_turn(message: dict) -> dict:
        """Discriminated, versioned per-turn delivery (commit/ack/reveal/hint/etc.)."""
        return router.handle_turn(message)

    @mcp.tool
    def receive_move(message: dict) -> dict:
        """Compatibility alias: forwards to the exact ``receive_turn`` path."""
        return router.handle_turn(message)

    @mcp.tool
    def submit_audit(payload: dict) -> dict:
        """Final audit / result-agreement submission. Wire argument name is
        ``payload``, matching ``protocol_contract.md`` (was ``message`` --
        a real cross-repo mismatch, fixed post-Batch-4B)."""
        return router.handle_audit(payload)

    @mcp.tool
    def receive_control(message: dict) -> dict:
        """Optional out-of-band control signal (enqueued, gracefully accepted)."""
        return router.handle_control(message)

    return mcp, inbox


async def run_server_until_cancelled(mcp: FastMCP, host: str, port: int) -> None:
    """Run the HTTP server; kept only for older tests that cancel the task
    directly as a lightweight stand-in opponent server.

    Production code, and any test that needs a genuinely graceful stop (one
    that actually closes the listening socket -- a bare cancel here does
    not, see ``server_lifecycle``'s module docstring), should use
    ``server_lifecycle.ManagedServer`` instead."""
    await mcp.run_http_async(host=host, port=port, show_banner=False, log_level="warning")

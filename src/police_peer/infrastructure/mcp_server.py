"""Minimal real FastMCP HTTP server for this peer -- health, negotiate, and
config-hash comparison only. The full game-loop tool surface (receive_turn,
submit_audit, receive_control) is a later batch (see docs/PROTOCOL.md and
ADR-0012 on the receive_move alias).

Idempotency policy: a repeated message with the SAME correlation_id and THE
SAME payload is accepted again (idempotent replay); the same correlation_id
with a DIFFERENT payload is rejected as a conflicting duplicate.
"""

from __future__ import annotations

import queue

from fastmcp import FastMCP

from police_peer.domain.roles import Role

# Deliberately synchronous, no `import asyncio` needed here -- tool bodies are sync;
# FastMCP runs them appropriately on its own event loop.


class PeerInbox:
    """Thread-safe mailboxes filled by MCP tools, drained by the caller."""

    def __init__(self) -> None:
        self.declarations: queue.Queue = queue.Queue()
        self.proposals: queue.Queue = queue.Queue()
        self._seen_by_correlation_id: dict[str, dict] = {}

    def record_or_check_conflict(self, correlation_id: str, message: dict) -> bool:
        """Return True if this is a new or identical-repeat message; False if
        it conflicts with a previously-seen message under the same correlation_id."""
        previous = self._seen_by_correlation_id.get(correlation_id)
        if previous is not None and previous != message:
            return False
        self._seen_by_correlation_id[correlation_id] = message
        return True


def build_peer_server(role: Role, own_config_sha256: str) -> tuple[FastMCP, PeerInbox]:
    """A FastMCP app exposing this batch's minimal negotiation tool surface."""
    inbox = PeerInbox()
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

    return mcp, inbox


async def run_server_until_cancelled(mcp: FastMCP, host: str, port: int) -> None:
    """Run the HTTP server; intended to be wrapped in an asyncio.Task and
    cancelled for a clean shutdown (CancelledError is expected, not an error)."""
    await mcp.run_http_async(host=host, port=port, show_banner=False, log_level="warning")

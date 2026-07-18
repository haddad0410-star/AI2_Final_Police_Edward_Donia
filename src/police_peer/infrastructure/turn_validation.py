"""Validation + routing for the game-phase FastMCP tools (Batch 2, Phase 6).

One discriminated, versioned ``receive_turn`` envelope carries every per-turn
message (``message_type`` field); ``receive_move`` is a thin alias onto the same
path. Handlers validate schema/role/game_uid/sequence/state, detect duplicates,
enqueue into the bounded inbox, and return a quick synchronous ack. They NEVER
run strategy code, never hold a true opponent position, and never bypass the
lifecycle state machine -- they consult it to gate whether receiving is legal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerStateMachine
from police_peer.domain.state_machine.states import TERMINAL_STATES, PeerState
from police_peer.infrastructure import inbox as inbox_mod
from police_peer.infrastructure.inbox import PeerInbox

_LOG = logging.getLogger("police_peer.turn")

#: Every message_type carried by the single discriminated ``receive_turn`` tool.
KNOWN_TURN_TYPES = frozenset(
    {
        "commitment",
        "commitment_ack",
        "reveal",
        "hint",
        "scent",
        "barrier",
        "capture_claim",
        "capture_response",
    }
)

#: States in which this peer will not accept game messages at all.
_NON_RECEIVING = TERMINAL_STATES | {PeerState.INITIALIZING}

_REQUIRED_ENVELOPE = ("game_uid", "sender", "sub_game_number", "step", "sequence_id")


def _reject(code: str, reason: str) -> dict:
    _LOG.info("reject %s: %s", code, reason)
    return {"ok": False, "error_code": code, "reason": reason}


@dataclass(frozen=True, slots=True)
class TurnRouter:
    """Validates and routes incoming game-phase messages into ``inbox``."""

    inbox: PeerInbox
    machine: PeerStateMachine
    expected_opponent_role: Role
    expected_game_uid: str
    expected_config_sha256: str

    def _validate_envelope(self, message: dict) -> dict | None:
        if not isinstance(message, dict):
            return _reject("MALFORMED", "message must be an object")
        envelope = message.get("envelope")
        if not isinstance(envelope, dict):
            return _reject("MALFORMED", "missing envelope")
        missing = [k for k in _REQUIRED_ENVELOPE if k not in envelope]
        if missing:
            return _reject("MALFORMED", f"envelope missing {missing}")
        if envelope["sender"] != self.expected_opponent_role.value:
            return _reject("WRONG_ROLE", f"unexpected sender {envelope['sender']!r}")
        if envelope["game_uid"] != self.expected_game_uid:
            return _reject("WRONG_GAME_UID", "game_uid does not match this series")
        config_hash = message.get("config_sha256")
        if config_hash is not None and config_hash != self.expected_config_sha256:
            return _reject("CONFIG_MISMATCH", "config_sha256 does not match")
        if self.machine.state in _NON_RECEIVING:
            return _reject("WRONG_STATE", f"not accepting messages in {self.machine.state}")
        return None

    def _check_duplicate_and_sequence(
        self, key: tuple, sender: str, sub_game_number: int, seq: int, message: dict
    ):
        status = self.inbox.duplicate_status(key, message)
        if status == inbox_mod.CONFLICT:
            return _reject("CONFLICTING_DUPLICATE", f"different payload for {key}")
        if status == inbox_mod.IDENTICAL:
            return {"ok": True, "duplicate": True}
        seq_status = self.inbox.sequence_status(sender, sub_game_number, seq)
        if seq_status == inbox_mod.SEQ_STALE:
            return _reject("STALE_SEQUENCE", f"sequence_id {seq} is stale")
        if seq_status == inbox_mod.SEQ_SKIPPED:
            return _reject("SKIPPED_SEQUENCE", f"sequence_id {seq} skips a required phase")
        return None

    def handle_turn(self, message: dict) -> dict:
        """Validate and enqueue one discriminated turn message; quick ack."""
        rejection = self._validate_envelope(message)
        if rejection is not None:
            return rejection
        message_type = message.get("message_type")
        if message_type not in KNOWN_TURN_TYPES:
            return _reject("UNKNOWN_TYPE", f"unknown message_type {message_type!r}")
        if self.inbox.is_full():
            return _reject("QUEUE_FULL", "inbox capacity reached")
        env = message["envelope"]
        sender, seq = env["sender"], env["sequence_id"]
        sub_game_number = env["sub_game_number"]
        key = (sub_game_number, env["step"], sender, message_type)
        early = self._check_duplicate_and_sequence(key, sender, sub_game_number, seq, message)
        if early is not None:
            return early
        self.inbox.remember(key, message)
        self.inbox.advance_sequence(sender, sub_game_number, seq)
        self.inbox.enqueue_turn(message)
        _LOG.info("accepted turn message_type=%s key=%s", message_type, key)
        return {"ok": True, "duplicate": False}

    def handle_audit(self, message: dict) -> dict:
        """Validate and enqueue a final-audit / result-agreement submission."""
        rejection = self._validate_envelope(message)
        if rejection is not None:
            return rejection
        if "records" not in message and message.get("message_type") != "result_agreement":
            return _reject("MALFORMED", "audit needs records or a result_agreement type")
        if self.inbox.is_full():
            return _reject("QUEUE_FULL", "inbox capacity reached")
        self.inbox.enqueue_audit(message)
        return {"ok": True}

    def handle_control(self, message: dict) -> dict:
        """Enqueue an optional control signal; gracefully accepted, never blocking."""
        if not isinstance(message, dict) or "kind" not in message:
            return _reject("MALFORMED", "control message needs a kind")
        if self.inbox.is_full():
            return _reject("QUEUE_FULL", "inbox capacity reached")
        self.inbox.enqueue_control(message)
        return {"ok": True}

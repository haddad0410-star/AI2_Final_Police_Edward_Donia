"""Thread-safe, bounded inboxes plus idempotency/sequence bookkeeping.

The FastMCP tool handlers never process a turn synchronously: they validate,
drop the message into one of these bounded queues, and ack immediately. The
local runtime (Phase 9) drains them. Bounding the queues is a DOS/back-pressure
defence -- once full, new messages are rejected rather than growing memory
without limit.
"""

from __future__ import annotations

import queue
from collections import deque
from typing import Any

#: Duplicate classification for an already-seen idempotency key.
NEW = "new"
IDENTICAL = "identical"
CONFLICT = "conflict"

#: Per-sender sequence classification.
SEQ_OK = "ok"
SEQ_STALE = "stale"
SEQ_SKIPPED = "skipped"


class PeerInbox:
    """Mailboxes for handshake AND game-phase messages, with duplicate/sequence guards."""

    def __init__(self, queue_capacity: int = 100) -> None:
        self.declarations: queue.Queue = queue.Queue()
        self.proposals: queue.Queue = queue.Queue()
        self.turn_messages: deque[dict] = deque()
        self.audits: deque[dict] = deque()
        self.controls: deque[dict] = deque()
        self._capacity = queue_capacity
        self._seen_by_correlation_id: dict[str, dict] = {}
        self._seen_turn_keys: dict[tuple, dict] = {}
        self._next_seq: dict[str, int] = {}

    # -- handshake idempotency (Batch 1, unchanged behaviour) -----------------
    def record_or_check_conflict(self, correlation_id: str, message: dict) -> bool:
        """True if new/identical-repeat; False if it conflicts under the same id."""
        previous = self._seen_by_correlation_id.get(correlation_id)
        if previous is not None and previous != message:
            return False
        self._seen_by_correlation_id[correlation_id] = message
        return True

    # -- game-phase back-pressure --------------------------------------------
    def depth(self) -> int:
        """Total queued game-phase messages across all three game queues."""
        return len(self.turn_messages) + len(self.audits) + len(self.controls)

    def is_full(self) -> bool:
        """True once the bounded capacity is reached (reject further messages)."""
        return self.depth() >= self._capacity

    # -- idempotency for turn messages ---------------------------------------
    def duplicate_status(self, key: tuple, payload: dict) -> str:
        """Classify ``payload`` under logical ``key`` as new/identical/conflict."""
        previous = self._seen_turn_keys.get(key)
        if previous is None:
            return NEW
        return IDENTICAL if previous == payload else CONFLICT

    def remember(self, key: tuple, payload: dict) -> None:
        """Record ``payload`` as the canonical content for ``key``."""
        self._seen_turn_keys[key] = payload

    # -- per-sender sequence monotonicity ------------------------------------
    def sequence_status(self, sender: str, sub_game_number: int, sequence_id: int) -> str:
        """Classify a sequence id as ok / stale (rewind) / skipped (gap).

        Scoped per ``(sub_game_number, sender)`` -- each sub-game is a fresh
        cryptographic/sequential context (a new series sub-game legitimately
        restarts ``sequence_id`` at 0), matching the per-sub-game cursor the
        opponent's own receiving sequence tracker already uses."""
        expected = self._next_seq.get((sub_game_number, sender), 0)
        if sequence_id < expected:
            return SEQ_STALE
        if sequence_id > expected:
            return SEQ_SKIPPED
        return SEQ_OK

    def advance_sequence(self, sender: str, sub_game_number: int, sequence_id: int) -> None:
        """Advance the expected next sequence id for ``(sub_game_number, sender)``."""
        self._next_seq[(sub_game_number, sender)] = sequence_id + 1

    # -- enqueue helpers ------------------------------------------------------
    def enqueue_turn(self, item: dict[str, Any]) -> None:
        self.turn_messages.append(item)

    def enqueue_audit(self, item: dict[str, Any]) -> None:
        self.audits.append(item)

    def enqueue_control(self, item: dict[str, Any]) -> None:
        self.controls.append(item)

"""Phase 6: game-phase message validation/routing via TurnRouter (in-process)."""

from __future__ import annotations

from police_peer.domain.roles import Role
from police_peer.domain.state_machine import PeerState, PeerStateMachine
from police_peer.infrastructure.inbox import PeerInbox
from police_peer.infrastructure.turn_validation import TurnRouter

GAME_UID = "uid-123"
CONFIG_HASH = "a" * 64


def _router(capacity: int = 100) -> tuple[TurnRouter, PeerInbox]:
    inbox = PeerInbox(queue_capacity=capacity)
    machine = PeerStateMachine(initial=PeerState.WAITING)
    router = TurnRouter(
        inbox=inbox,
        machine=machine,
        expected_opponent_role=Role.THIEF,
        expected_game_uid=GAME_UID,
        expected_config_sha256=CONFIG_HASH,
    )
    return router, inbox


def _msg(message_type: str, step: int, seq: int, sender: str = "thief", **extra) -> dict:
    return {
        "message_type": message_type,
        "envelope": {
            "game_uid": GAME_UID,
            "sender": sender,
            "sub_game_number": 1,
            "step": step,
            "sequence_id": seq,
        },
        **extra,
    }


def test_normal_turn_lifecycle_enqueues_in_order() -> None:
    router, inbox = _router()
    assert router.handle_turn(_msg("commitment", 0, 0))["ok"] is True
    assert router.handle_turn(_msg("commitment_ack", 0, 1))["ok"] is True
    assert router.handle_turn(_msg("reveal", 0, 2))["ok"] is True
    assert [m["message_type"] for m in inbox.turn_messages] == [
        "commitment",
        "commitment_ack",
        "reveal",
    ]


def test_duplicate_identical_is_idempotent() -> None:
    router, inbox = _router()
    first = router.handle_turn(_msg("commitment", 0, 0))
    second = router.handle_turn(_msg("commitment", 0, 0))
    assert first == {"ok": True, "duplicate": False}
    assert second == {"ok": True, "duplicate": True}
    assert len(inbox.turn_messages) == 1  # not enqueued twice


def test_duplicate_conflicting_is_rejected() -> None:
    router, _ = _router()
    router.handle_turn(_msg("commitment", 0, 0, commit_hash="x"))
    conflict = router.handle_turn(_msg("commitment", 0, 0, commit_hash="y"))
    assert conflict["ok"] is False
    assert conflict["error_code"] == "CONFLICTING_DUPLICATE"


def test_stale_sequence_is_rejected() -> None:
    router, _ = _router()
    router.handle_turn(_msg("commitment", 0, 0))
    router.handle_turn(_msg("commitment_ack", 0, 1))
    stale = router.handle_turn(_msg("reveal", 0, 0))  # sequence rewinds
    assert stale["error_code"] == "STALE_SEQUENCE"


def test_skipped_sequence_is_rejected() -> None:
    router, _ = _router()
    router.handle_turn(_msg("commitment", 0, 0))
    skipped = router.handle_turn(_msg("reveal", 0, 5))  # jumps past required phases
    assert skipped["error_code"] == "SKIPPED_SEQUENCE"


def test_out_of_order_reveal_rejected_via_sequence() -> None:
    router, _ = _router()
    # reveal arriving as the very first message (seq 3) skips commit/ack
    out_of_order = router.handle_turn(_msg("reveal", 0, 3))
    assert out_of_order["error_code"] == "SKIPPED_SEQUENCE"


def test_wrong_role_rejected() -> None:
    router, _ = _router()
    assert (
        router.handle_turn(_msg("commitment", 0, 0, sender="police"))["error_code"] == "WRONG_ROLE"
    )


def test_wrong_game_uid_rejected() -> None:
    router, _ = _router()
    bad = _msg("commitment", 0, 0)
    bad["envelope"]["game_uid"] = "other-uid"
    assert router.handle_turn(bad)["error_code"] == "WRONG_GAME_UID"


def test_config_mismatch_rejected() -> None:
    router, _ = _router()
    assert router.handle_turn(_msg("commitment", 0, 0, config_sha256="b" * 64))["error_code"] == (
        "CONFIG_MISMATCH"
    )


def test_malformed_schema_rejected() -> None:
    router, _ = _router()
    assert router.handle_turn({"nonsense": True})["error_code"] == "MALFORMED"
    assert router.handle_turn(_msg("bogus_type", 0, 0))["error_code"] == "UNKNOWN_TYPE"


def test_receiving_blocked_in_terminal_state() -> None:
    inbox = PeerInbox()
    machine = PeerStateMachine(initial=PeerState.INITIALIZING)
    router = TurnRouter(inbox, machine, Role.THIEF, GAME_UID, CONFIG_HASH)
    assert router.handle_turn(_msg("commitment", 0, 0))["error_code"] == "WRONG_STATE"


def test_capture_response_round_trip() -> None:
    # ``capture_claim`` travels bundled inside a ``reveal`` body (see
    # SealedTurnPayload.public_reveal_dict()), never as its own message
    # type; only ``capture_response`` is a real standalone type (Batch 3.5
    # Task 4, audit finding B1 -- dead scaffolding removed).
    router, inbox = _router()
    router.handle_turn(_msg("reveal", 0, 0))
    router.handle_turn(_msg("capture_response", 0, 1, caught=False))
    assert [m["message_type"] for m in inbox.turn_messages] == [
        "reveal",
        "capture_response",
    ]


def test_audit_submission_round_trip() -> None:
    router, inbox = _router()
    audit = {
        "message_type": "audit",
        "envelope": _msg("commitment", 0, 0)["envelope"],
        "records": [{"step": 0}],
    }
    assert router.handle_audit(audit)["ok"] is True
    assert len(inbox.audits) == 1


def test_control_message_accepted() -> None:
    router, inbox = _router()
    assert router.handle_control({"kind": "status", "status_text": "ready"})["ok"] is True
    assert len(inbox.controls) == 1
    assert router.handle_control({"no_kind": True})["error_code"] == "MALFORMED"


def test_queue_full_back_pressure() -> None:
    router, inbox = _router(capacity=2)
    router.handle_turn(_msg("commitment", 0, 0))
    router.handle_turn(_msg("commitment_ack", 0, 1))
    full = router.handle_turn(_msg("reveal", 0, 2))
    assert full["error_code"] == "QUEUE_FULL"
    assert inbox.depth() == 2

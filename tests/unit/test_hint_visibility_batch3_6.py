"""Batch 3.6 Task 4: end-to-end hint-verdict visibility proof, using the
real SealedTurnSession commit/ack/reveal/audit state machine (not a direct
dataclass check) -- the intent verdict must be absent at the live reveal
phase but present and verifiable at the final audit phase.
"""

from __future__ import annotations

import dataclasses

from police_peer.domain.crypto import SealedTurnSession, compute_commit_hash, verify_commit
from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.domain.crypto.sealing import digest_scent_grid


def _payload(intent: str = "lie") -> SealedTurnPayload:
    grid = tuple(tuple(0.0 for _ in range(7)) for _ in range(7))
    return SealedTurnPayload(
        step=0,
        role="police",
        sub_game_number=1,
        position=(0, 0),
        move="N",
        barrier_placed=None,
        intent=intent,
        hint="the eastern quarter looks promising",
        scent_digest=digest_scent_grid(grid),
        scent_grid=grid,
        capture_claim=None,
        claim_response=None,
        win_claim=False,
        config_sha256="f" * 64,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce="e" * 64,
    )


def test_live_reveal_omits_intent_but_final_audit_reveals_it() -> None:
    session = SealedTurnSession(_payload(intent="lie"))
    session.commit()
    session.acknowledge()
    live_reveal = session.reveal()
    assert "intent" not in live_reveal
    assert live_reveal["hint"] == "the eastern quarter looks promising"

    record = session.audit_reveal()
    assert record.payload.intent == "lie"  # final audit CAN see the verdict
    assert (
        verify_commit(record.payload, record.commit_hash) is True
    )  # and verify it cryptographically


def test_final_audit_detects_a_forged_intent() -> None:
    honest = _payload(intent="lie")
    committed_hash = compute_commit_hash(honest)
    forged = dataclasses.replace(honest, intent="truth")
    assert verify_commit(forged, committed_hash) is False


def test_live_reveal_never_contains_nonce_or_intent_together() -> None:
    """Both fields withheld at reveal must remain withheld regardless of
    which HintIntent value was actually sealed."""
    for intent in ("truth", "lie"):
        session = SealedTurnSession(_payload(intent=intent))
        session.commit()
        session.acknowledge()
        revealed = session.reveal()
        assert "nonce" not in revealed
        assert "intent" not in revealed

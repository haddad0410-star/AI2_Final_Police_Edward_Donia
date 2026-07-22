"""Phase 4: commit/reveal cryptography, tamper detection, and the mutual audit.

The FIXED nonce below is a TEST-ONLY constant so hashes are deterministic;
production code always calls the real CSPRNG (``generate_nonce``).
"""

from __future__ import annotations

import dataclasses

import pytest

from police_peer.domain.crypto import (
    AuditVerdict,
    SealedRecord,
    SealedTurnPayload,
    SealedTurnSession,
    SealError,
    audit_records,
    compute_commit_hash,
    digest_scent_grid,
    generate_nonce,
    verify_commit,
)
from police_peer.domain.crypto import sealing as sealing_module

# TEST-ONLY fixed nonce -- never used in production.
FIXED_NONCE = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"


def _payload(**overrides) -> SealedTurnPayload:
    base = {
        "step": 3,
        "role": "police",
        "sub_game_number": 1,
        "position": (0, 0),
        "move": "N",
        "barrier_placed": None,
        "intent": "truth",
        "hint": "The northern lanes feel promising.",
        "scent_digest": digest_scent_grid(((0.0, 0.1), (0.2, 0.9))),
        "scent_grid": ((0.0, 0.1), (0.2, 0.9)),
        "capture_claim": None,
        "claim_response": None,
        "win_claim": False,
        "config_sha256": "cafef00d",
        "timestamp": "2026-07-18T00:00:00+00:00",
        "nonce": FIXED_NONCE,
    }
    base.update(overrides)
    return SealedTurnPayload(**base)


def test_commit_hash_is_stable_and_hex() -> None:
    h = compute_commit_hash(_payload())
    assert len(h) == 64
    assert h == compute_commit_hash(_payload())  # deterministic given fixed nonce


def test_valid_complete_audit_succeeds() -> None:
    records = [
        SealedRecord(
            _payload(step=s, nonce=f"{s:064x}"),
            compute_commit_hash(_payload(step=s, nonce=f"{s:064x}")),
        )
        for s in range(3)
    ]
    result = audit_records(records)
    assert result.verdict is AuditVerdict.VERIFIED
    assert result.ok is True


def test_each_field_mutation_is_detected() -> None:
    original = _payload()
    original_hash = compute_commit_hash(original)
    mutations = {
        "move": "S",
        "hint": "A different lie about the west.",
        "intent": "lie",
        "scent_digest": digest_scent_grid(((0.9, 0.0), (0.0, 0.0))),
        "barrier_placed": (1, 1),
        "capture_claim": (2, 2),
        "step": 4,
        "role": "thief",
        "timestamp": "2026-07-18T00:00:01+00:00",
        "nonce": "ff" * 32,
        "claim_response": True,
        "win_claim": True,
        "position": (5, 5),
        "config_sha256": "deadbeef",
    }
    for field, value in mutations.items():
        mutated = dataclasses.replace(original, **{field: value})
        assert verify_commit(mutated, original_hash) is False, field


def test_config_sha256_mutation_is_detected() -> None:
    """config_sha256 is now a real top-level field (Batch 4B Task 3 --
    previously nested inside `state`, the primary source of the
    Police/Thief cross-schema divergence)."""
    original = _payload()
    original_hash = compute_commit_hash(original)
    mutated = dataclasses.replace(original, config_sha256="deadbeef")
    assert verify_commit(mutated, original_hash) is False


def test_fresh_nonce_per_record() -> None:
    nonces = {generate_nonce() for _ in range(200)}
    assert len(nonces) == 200
    assert all(len(n) == 64 for n in nonces)


def test_nonce_reuse_detected_by_audit() -> None:
    a = _payload(step=0, nonce=FIXED_NONCE)
    b = _payload(step=1, nonce=FIXED_NONCE)  # reused nonce
    records = [
        SealedRecord(a, compute_commit_hash(a)),
        SealedRecord(b, compute_commit_hash(b)),
    ]
    result = audit_records(records)
    assert result.verdict is AuditVerdict.TAMPER_FORFEIT
    assert "nonce reuse" in result.reason


def test_incomplete_reveal_missing_nonce_detected() -> None:
    p = _payload(nonce="")
    result = audit_records([SealedRecord(p, "0" * 64)])
    assert result.verdict is AuditVerdict.TAMPER_FORFEIT
    assert "missing nonce" in result.reason


def test_duplicate_reveal_detected() -> None:
    p = _payload(step=0, nonce=f"{0:064x}")
    h = compute_commit_hash(p)
    result = audit_records([SealedRecord(p, h), SealedRecord(p, h)])
    assert result.verdict is AuditVerdict.TAMPER_FORFEIT
    assert "duplicate reveal" in result.reason


def test_missing_step_creates_sequence_gap() -> None:
    records = []
    for s in (0, 1, 3):  # step 2 dropped
        p = _payload(step=s, nonce=f"{s:064x}")
        records.append(SealedRecord(p, compute_commit_hash(p)))
    result = audit_records(records)
    assert result.verdict is AuditVerdict.TAMPER_FORFEIT
    assert "sequence gap" in result.reason


def test_canonical_dictionary_ordering_is_key_independent() -> None:
    """Hash depends on content, not on Python dict insertion order."""
    p1 = _payload()
    # Rebuild an equivalent payload; canonical_json sorts keys regardless.
    p2 = SealedTurnPayload(**dataclasses.asdict(p1))
    assert compute_commit_hash(p1) == compute_commit_hash(p2)


def test_hebrew_hint_canonicalization_round_trips() -> None:
    hebrew = _payload(hint="הגנב נע מערבה")  # "the thief moves west"
    h = compute_commit_hash(hebrew)
    # An identical Hebrew hint reproduces the same hash (UTF-8 canonical).
    assert verify_commit(_payload(hint="הגנב נע מערבה"), h) is True
    # A changed Hebrew hint does not.
    assert verify_commit(_payload(hint="הגנב נע צפונה"), h) is False


def test_constant_time_compare_is_actually_used(monkeypatch) -> None:
    calls = {"n": 0}
    real = sealing_module.secrets.compare_digest

    def spy(a, b):
        calls["n"] += 1
        return real(a, b)

    monkeypatch.setattr(sealing_module.secrets, "compare_digest", spy)
    verify_commit(_payload(), compute_commit_hash(_payload()))
    assert calls["n"] == 1


def test_session_enforces_commit_ack_reveal_audit_order() -> None:
    session = SealedTurnSession(_payload())
    commit_hash = session.commit()
    assert len(commit_hash) == 64
    session.acknowledge()
    revealed = session.reveal()
    assert "nonce" not in revealed  # nonce withheld at reveal
    assert revealed["move"] == "N"
    record = session.audit_reveal()
    assert record.payload.nonce == FIXED_NONCE
    assert verify_commit(record.payload, record.commit_hash) is True


def test_reveal_before_acknowledgment_is_rejected() -> None:
    session = SealedTurnSession(_payload())
    session.commit()
    with pytest.raises(SealError):
        session.reveal()  # no acknowledge() yet


def test_commit_is_only_thing_sent_first() -> None:
    """The commit step exposes a hash only -- not the underlying fields."""
    session = SealedTurnSession(_payload())
    sent = session.commit()
    assert isinstance(sent, str) and len(sent) == 64

"""Builders for the sealed payload and wire messages of one turn.

Kept separate from the turn loop so the loop stays small. The capture claim is
always made at THIS peer's own destination cell -- a truthful "am I on you?"
question, never a fabricated assertion that the opponent is caught.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from police_peer.domain.crypto import SealedTurnPayload, generate_nonce
from police_peer.domain.crypto.sealing import digest_scent_grid
from police_peer.domain.hints import Hint
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import ScentField
from police_peer.strategy.decision import Decision


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_payload(
    *,
    role: Role,
    step: int,
    sub_game_number: int,
    destination: Position,
    decision: Decision,
    hint: Hint,
    own_scent: ScentField,
    config_sha256: str,
) -> SealedTurnPayload:
    """Assemble the fully-sealed per-step payload (nonce freshly generated)."""
    barrier = (decision.barrier.row, decision.barrier.col) if decision.barrier else None
    return SealedTurnPayload(
        step=step,
        role=role.value,
        sub_game_number=sub_game_number,
        state={"position": [destination.row, destination.col], "config_sha256": config_sha256},
        move=decision.direction.value,
        barrier_placed=barrier,
        intent=hint.intent.value,
        hint=hint.text,
        scent_digest=digest_scent_grid(own_scent.grid),
        scent_grid=own_scent.grid,
        capture_claim=(destination.row, destination.col),
        claim_response=None,
        win_claim=False,
        timestamp=_now_iso(),
        nonce=generate_nonce(),
    )


def envelope(
    game_uid: str, sender: Role, sub_game_number: int, step: int, sequence_id: int
) -> dict[str, Any]:
    """The wire envelope shared by our commitment and reveal messages."""
    return {
        "game_uid": game_uid,
        "sender": sender.value,
        "sub_game_number": sub_game_number,
        "step": step,
        "sequence_id": sequence_id,
    }


def commitment_message(env: dict, commit_hash: str) -> dict[str, Any]:
    """Step-1 message: H_commit only."""
    return {"message_type": "commitment", "envelope": env, "commit_hash": commit_hash}


def reveal_message(env: dict, reveal: dict) -> dict[str, Any]:
    """Step-3 message: move + hint in the clear (nonce still withheld)."""
    return {"message_type": "reveal", "envelope": env, "reveal": reveal}

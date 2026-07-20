"""The versioned, canonical sealed-turn payload (Phase 4; scent/intent sealing
repaired Batch 3.5 Task 4/5 -- see
``integration_lab/evidence/batch3_5/observation_pipeline_audit.md`` defects
A1/C2).

This is the exact field set hashed into ``H_commit`` per
``integration_lab/audit/protocol_contract.md`` section 3.2 (the binding field
set names the actual ``smell_grid`` -- our own decaying scent trail -- as a
sealed field, not merely a digest of it). Every key is always present
(``None`` where inapplicable to the sender's role) so that two
independently-implemented peers canonicalize a byte-identical dict and recompute
identical hashes. It NEVER contains the opponent's true position -- only this
peer's own legally-sealable state, move, and public declarations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Bump when the sealed field set changes; both peers must agree on it.
SCHEMA_VERSION = "commit-reveal/2"


@dataclass(frozen=True, slots=True)
class SealedTurnPayload:
    """One step's fully-sealed record.

    ``nonce`` and ``intent`` are both withheld from the same-turn public
    reveal and disclosed only at the final audit (``intent`` -- the hint's
    truth/lie verdict -- must stay sealed during play per the absolute rule
    "truth/lie intent sealed"; a receiver must judge hint reliability from
    consistency history, never from an early-disclosed verdict).
    """

    step: int
    role: str
    sub_game_number: int
    state: Any
    move: str | None
    barrier_placed: tuple[int, int] | None
    intent: str
    hint: str
    scent_digest: str
    scent_grid: tuple[tuple[float, ...], ...]
    capture_claim: tuple[int, int] | None
    claim_response: bool | None
    win_claim: bool
    timestamp: str
    nonce: str
    schema_version: str = SCHEMA_VERSION

    def to_canonical_dict(self) -> dict[str, Any]:
        """The exact dict fed to ``canonical_json`` before hashing.

        Tuples are converted to lists so the JSON round-trips identically on a
        peer that reconstructs the payload from parsed JSON.
        """
        return {
            "schema_version": self.schema_version,
            "step": self.step,
            "role": self.role,
            "sub_game_number": self.sub_game_number,
            "state": self.state,
            "move": self.move,
            "barrier_placed": list(self.barrier_placed) if self.barrier_placed else None,
            "intent": self.intent,
            "hint": self.hint,
            "scent_digest": self.scent_digest,
            "scent_grid": [list(row) for row in self.scent_grid],
            "capture_claim": list(self.capture_claim) if self.capture_claim else None,
            "claim_response": self.claim_response,
            "win_claim": self.win_claim,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }

    def public_reveal_dict(self) -> dict[str, Any]:
        """Fields revealed at step 3 (move + hint + scent grid in clear);
        ``nonce`` and ``intent`` stay hidden until the final audit."""
        full = self.to_canonical_dict()
        del full["nonce"]
        del full["intent"]
        return full

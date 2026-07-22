"""The versioned, canonical sealed-turn payload.

Batch 4B Task 3: the sealed field set is now ``commitment/1`` -- a single,
role-agnostic canonical shape both this repo and the independently-built
Thief repo adopt for newly-sealed records, resolving the two mechanical
divergences documented in
``integration_lab/evidence/batch4b/commitment_schema_audit.md`` (the
``state`` field's shape -- dict here vs an opaque string in Thief -- and
``config_sha256``'s placement -- nested inside ``state`` here vs a
top-level field in Thief). Both are fixed by replacing ``state`` with a
plain ``position`` tuple and promoting ``config_sha256`` to a real
top-level field, matching Thief's (already cleaner) convention. See
``integration_lab/evidence/batch4b/canonical_commitment_design.md`` for
the full design rationale.

Legacy note: records sealed under the prior ``commit-reveal/2`` schema
(Batch 1-4A evidence) are UNCHANGED on disk and remain self-verifiable by
this repo under their own original schema
(``services/replay_checks.py::payload_from_step`` still reconstructs them
correctly) -- only NEWLY sealed records use ``commitment/1``.

Every key is always present (``None``/``False`` where inapplicable to the
sender's role) so that two independently-implemented peers canonicalize a
byte-identical dict and recompute identical hashes. It NEVER contains the
opponent's true position -- only this peer's own legally-sealable state,
move, and public declarations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Bump when the sealed field set changes; both peers must agree on it.
SCHEMA_VERSION = "commitment/1"

#: The exact field set of a ``commitment/1`` canonical dict -- used to
#: reject unknown fields that could otherwise silently alter a commitment.
CANONICAL_FIELD_SET = frozenset(
    {
        "schema_version",
        "step",
        "role",
        "sub_game_number",
        "position",
        "move",
        "barrier_placed",
        "intent",
        "hint",
        "scent_digest",
        "scent_grid",
        "capture_claim",
        "claim_response",
        "win_claim",
        "config_sha256",
        "timestamp",
        "nonce",
    }
)


@dataclass(frozen=True, slots=True)
class SealedTurnPayload:
    """One step's fully-sealed record (``commitment/1``).

    ``nonce`` and ``intent`` are both withheld from the same-turn public
    reveal and disclosed only at the final audit (``intent`` -- the hint's
    truth/lie verdict -- must stay sealed during play per the absolute rule
    "truth/lie intent sealed"; a receiver must judge hint reliability from
    consistency history, never from an early-disclosed verdict).

    Role-specific fields (``barrier_placed``/``capture_claim`` are
    Police-only in practice; ``claim_response``/``win_claim`` are
    Thief-only in practice) are always present as keys, explicit ``None``
    (or ``False`` for ``win_claim``) when inapplicable to the sealing
    peer's role -- never omitted, so both sides' canonicalization always
    produces the same key set.
    """

    step: int
    role: str
    sub_game_number: int
    position: tuple[int, int]
    move: str | None
    barrier_placed: tuple[int, int] | None
    intent: str
    hint: str
    scent_digest: str
    scent_grid: tuple[tuple[float, ...], ...]
    capture_claim: tuple[int, int] | None
    claim_response: bool | None
    win_claim: bool
    config_sha256: str
    timestamp: str
    nonce: str
    schema_version: str = SCHEMA_VERSION

    def to_canonical_dict(self) -> dict[str, Any]:
        """The exact dict fed to ``canonical_json`` before hashing.

        Tuples are converted to lists so the JSON round-trips identically on a
        peer that reconstructs the payload from parsed JSON. Schema-version
        aware: a record reconstructed from LEGACY ``commit-reveal/1``/``/2``
        evidence must canonicalize back into that legacy shape (``state``
        nested dict, no top-level ``position``/``config_sha256``) so its
        original commitment hash still recomputes correctly -- only
        ``commitment/1`` (the current schema) uses the new flat shape. This
        is what keeps Batch 1-4A evidence self-verifiable without rewriting
        any file on disk.
        """
        if self.schema_version in ("commit-reveal/1", "commit-reveal/2"):
            return {
                "schema_version": self.schema_version,
                "step": self.step,
                "role": self.role,
                "sub_game_number": self.sub_game_number,
                "state": {"position": list(self.position), "config_sha256": self.config_sha256}
                if self.schema_version == "commit-reveal/2"
                else {"position": list(self.position)},
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
        return {
            "schema_version": self.schema_version,
            "step": self.step,
            "role": self.role,
            "sub_game_number": self.sub_game_number,
            "position": list(self.position),
            "move": self.move,
            "barrier_placed": list(self.barrier_placed) if self.barrier_placed else None,
            "intent": self.intent,
            "hint": self.hint,
            "scent_digest": self.scent_digest,
            "scent_grid": [list(row) for row in self.scent_grid],
            "capture_claim": list(self.capture_claim) if self.capture_claim else None,
            "claim_response": self.claim_response,
            "win_claim": self.win_claim,
            "config_sha256": self.config_sha256,
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

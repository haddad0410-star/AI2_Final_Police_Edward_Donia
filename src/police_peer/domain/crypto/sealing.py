"""Nonce generation, commitment hashing, and constant-time verification.

Cryptographic rules (Phase 4, non-negotiable): nonces come from ``secrets``
(a CSPRNG), never ``random``/``hash``/``repr``/``pickle``/timestamps;
verification uses ``secrets.compare_digest`` (constant-time); the hash is
``SHA256(canonical_json(payload))`` with sorted keys and fixed separators.
"""

from __future__ import annotations

import hashlib
import secrets

from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.shared.canonical_json import canonical_json_bytes

#: Nonce entropy in bytes; token_hex returns twice this many hex chars.
_NONCE_BYTES = 32


def generate_nonce() -> str:
    """A fresh, unpredictable per-step nonce from the OS CSPRNG."""
    return secrets.token_hex(_NONCE_BYTES)


def compute_commit_hash(payload: SealedTurnPayload) -> str:
    """``H_commit = SHA256(canonical_json(payload))`` as lowercase hex."""
    return hashlib.sha256(canonical_json_bytes(payload.to_canonical_dict())).hexdigest()


def digest_scent_grid(grid: tuple[tuple[float, ...], ...]) -> str:
    """A stable digest of a scent grid, sealed instead of the full grid.

    Rounds each value to a fixed precision first so that two peers computing the
    same physical grid produce a byte-identical digest despite float formatting.
    """
    rounded = [[round(value, 6) for value in row] for row in grid]
    return hashlib.sha256(canonical_json_bytes(rounded)).hexdigest()


def verify_commit(payload: SealedTurnPayload, expected_hash: str) -> bool:
    """Constant-time check that ``payload`` recomputes to ``expected_hash``."""
    recomputed = compute_commit_hash(payload)
    return secrets.compare_digest(recomputed, expected_hash)

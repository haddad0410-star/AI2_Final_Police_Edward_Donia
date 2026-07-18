"""Nonce-based Step-0 commit/reveal sealing and cross-check for the
canonical declaration (session recovery step C). Split out of
``declaration.py`` to stay under the 150-line cap.
"""

from __future__ import annotations

import secrets

from police_peer.domain.declaration import SCHEMA_VERSION, PeerDeclaration
from police_peer.shared.canonical_json import canonical_sha256_hex


def seal_declaration(declaration: PeerDeclaration, nonce: str) -> str:
    """Commit hash over the declaration + a hidden nonce (Phase 4 canonical hash)."""
    payload = {**declaration.to_dict(), "nonce": nonce}
    return canonical_sha256_hex(payload)


def verify_declaration(declaration: PeerDeclaration, nonce: str, expected_hash: str) -> bool:
    """Constant-time check that a declaration reseals to ``expected_hash``."""
    return secrets.compare_digest(seal_declaration(declaration, nonce), expected_hash)


def generate_declaration_nonce() -> str:
    """A fresh CSPRNG nonce for sealing the declaration (never a timestamp)."""
    return secrets.token_hex(32)


def declaration_mismatches(
    declaration: PeerDeclaration,
    expected_config_sha256: str,
    expected_group_ids: frozenset[str],
    expected_schema_version: str = SCHEMA_VERSION,
) -> list[str]:
    """Return human-readable reasons an incoming declaration is inconsistent."""
    reasons: list[str] = []
    if declaration.shared_config_sha256 != expected_config_sha256:
        reasons.append("shared_config_sha256 mismatch")
    if declaration.group_id not in expected_group_ids:
        reasons.append(f"unexpected group_id {declaration.group_id!r}")
    if declaration.schema_version != expected_schema_version:
        reasons.append("schema_version mismatch")
    return reasons

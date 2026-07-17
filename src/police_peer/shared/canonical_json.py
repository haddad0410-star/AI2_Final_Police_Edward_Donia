"""Canonical JSON serialization (ADR-0003): sorted keys, fixed separators, UTF-8.

Used wherever two independent peers must hash byte-identical input from the
same logical data (protocol message signing in a later batch, and here for
computing a stable digest of an in-memory config/message object). Not to be
confused with `config_loader.sha256_hex`, which hashes a file's raw bytes as
written on disk rather than a re-serialized in-memory structure.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(data: Any) -> bytes:
    """Serialize `data` as canonical JSON: sorted keys, compact separators."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_sha256_hex(data: Any) -> str:
    """SHA-256 hex digest of `data`'s canonical JSON encoding."""
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()

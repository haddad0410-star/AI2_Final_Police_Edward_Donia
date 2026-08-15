"""Isolated, opt-in commitment construction for the UNCOUNTED sharNamr
friendly only. NOT imported by any production match-running path
(game_runner.py, series_runtime.py, subgame_runtime.py, http_transport.py) --
the default/counted-match commitment scheme in sealing.py is unchanged and
unaffected by this module's existence.

sharNamr's documented construction: SHA256(canonical_json(payload) + "|" +
nonce), nonce appended as raw UTF-8 bytes after the canonical JSON, rather
than embedded as a payload field (contrast sealing.py's
H = SHA256(canonical_json(state, move, intent, nonce)), the book-cited
formula, Ch.5.3/App.E rule 17, where nonce IS a field inside the canonicalized
object).
"""

from __future__ import annotations

import hashlib
import json


def canonical_json_bytes_friendly_external(value: object) -> bytes:
    """Byte-identical to sharNamr's stated canonicalization:
    json.dumps(value, sort_keys=True, ensure_ascii=False,
    separators=(",", ":"), allow_nan=False), UTF-8 encoded."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def compute_commit_hash_friendly_external(payload: dict, nonce: str) -> str:
    """H = SHA256(canonical_json(payload) + b"|" + nonce.encode()). `payload`
    must NOT itself contain a `nonce` key (sharNamr's payload and nonce are
    disjoint inputs, unlike our own SealedTurnPayload)."""
    if "nonce" in payload:
        raise ValueError("friendly-external payload must not itself contain a 'nonce' key")
    body = canonical_json_bytes_friendly_external(payload)
    final_bytes = body + b"|" + nonce.encode("utf-8")
    return hashlib.sha256(final_bytes).hexdigest()

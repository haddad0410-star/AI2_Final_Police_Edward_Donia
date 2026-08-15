"""Deterministic vectors for the isolated sharNamr-friendly-only commitment
construction. Proves exact byte sequence and digest -- and proves this module
is never imported by the production match-running path.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from police_peer.domain.crypto.sealing_friendly_external import (
    canonical_json_bytes_friendly_external,
    compute_commit_hash_friendly_external,
)


def test_canonical_json_matches_documented_construction() -> None:
    value = {"b": 1, "a": [1, 2, 3], "c": "hébrew ok"}
    result = canonical_json_bytes_friendly_external(value)
    expected = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    assert result == expected
    assert result == b'{"a":[1,2,3],"b":1,"c":"h\xc3\xa9brew ok"}'


def test_deterministic_vector_exact_bytes_and_digest() -> None:
    payload = {"step": 0, "sender": "police", "hint": "hi", "commit_target": True}
    nonce = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"

    canonical = canonical_json_bytes_friendly_external(payload)
    final_bytes = canonical + b"|" + nonce.encode("utf-8")
    expected_digest = hashlib.sha256(final_bytes).hexdigest()

    assert canonical == b'{"commit_target":true,"hint":"hi","sender":"police","step":0}'
    assert final_bytes == (
        b'{"commit_target":true,"hint":"hi","sender":"police","step":0}|'
        b"aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    )
    result = compute_commit_hash_friendly_external(payload, nonce)
    assert result == expected_digest
    assert len(result) == 64


def test_differs_from_our_production_formula() -> None:
    """Confirms this really IS the different formula -- not accidentally
    identical to sealing.py's compute_commit_hash for the same content."""
    payload = {"step": 0, "sender": "police"}
    nonce = "aa" * 32
    friendly_digest = compute_commit_hash_friendly_external(payload, nonce)

    payload_with_nonce_embedded = {**payload, "nonce": nonce}
    embedded_bytes = canonical_json_bytes_friendly_external(payload_with_nonce_embedded)
    embedded_digest = hashlib.sha256(embedded_bytes).hexdigest()

    assert friendly_digest != embedded_digest


def test_rejects_payload_that_already_contains_nonce() -> None:
    with pytest.raises(ValueError, match="nonce"):
        compute_commit_hash_friendly_external({"nonce": "x"}, "aa" * 32)


def test_never_imported_by_production_match_paths() -> None:
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[2] / "src" / "police_peer"
    offenders = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "sealing_friendly_external.py":
            continue
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "sealing_friendly_external" in node.module
            ):
                offenders.append(str(py_file))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "sealing_friendly_external" in alias.name:
                        offenders.append(str(py_file))
    assert offenders == [], (
        f"production code must not import the friendly-only adapter: {offenders}"
    )

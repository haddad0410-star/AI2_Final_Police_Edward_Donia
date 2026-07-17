"""Tests for canonical JSON serialization (ADR-0003)."""

from __future__ import annotations

from police_peer.shared.canonical_json import canonical_json_bytes, canonical_sha256_hex


def test_key_order_does_not_affect_output() -> None:
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_output_uses_compact_separators() -> None:
    encoded = canonical_json_bytes({"a": 1, "b": [1, 2]})
    assert b" " not in encoded


def test_hash_is_deterministic_across_key_order() -> None:
    a = {"z": 1, "a": {"y": 2, "x": 3}}
    b = {"a": {"x": 3, "y": 2}, "z": 1}
    assert canonical_sha256_hex(a) == canonical_sha256_hex(b)


def test_hash_changes_on_value_change() -> None:
    assert canonical_sha256_hex({"a": 1}) != canonical_sha256_hex({"a": 2})

"""Coverage for deterministic game_id / game_uid derivation."""

from __future__ import annotations

import uuid

from police_peer.services.game_ids import derive_game_id, derive_game_uid


def test_single_group_game_id() -> None:
    assert derive_game_id(["edward-donia"]) == "edward-donia"


def test_pair_game_id_is_sorted() -> None:
    assert derive_game_id(["zeta", "alpha"]) == "alpha-vs-zeta"


def test_empty_group_ids_fallback() -> None:
    assert derive_game_id([]) == "unknown"


def test_game_uid_is_valid_and_deterministic() -> None:
    sha = "a" * 64
    first = derive_game_uid(sha, ["b", "a"])
    second = derive_game_uid(sha, ["a", "b"])  # order-independent (sorted)
    assert first == second
    assert uuid.UUID(first)  # parses as a valid UUID


def test_game_uid_changes_with_config_hash() -> None:
    assert derive_game_uid("a" * 64, ["g"]) != derive_game_uid("b" * 64, ["g"])

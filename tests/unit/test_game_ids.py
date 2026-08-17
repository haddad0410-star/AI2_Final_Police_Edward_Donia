"""Coverage for deterministic game_id / game_uid derivation."""

from __future__ import annotations

import uuid
from pathlib import Path

from police_peer.services.game_ids import (
    canonical_terms_json,
    derive_game_id,
    derive_game_uid,
    terms_from_shared_config,
)
from police_peer.shared.config_loader import load_shared_config

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

_TERMS = {"board_size": 7, "num_games": 6}


def test_single_group_game_id() -> None:
    assert derive_game_id(["edward-donia"]) == "edward-donia"


def test_pair_game_id_is_sorted() -> None:
    assert derive_game_id(["zeta", "alpha"]) == "alpha-vs-zeta"


def test_empty_group_ids_fallback() -> None:
    assert derive_game_id([]) == "unknown"


def test_game_uid_is_valid_and_deterministic() -> None:
    first = derive_game_uid(_TERMS, ["b", "a"])
    second = derive_game_uid(_TERMS, ["a", "b"])  # order-independent (sorted)
    assert first == second
    assert uuid.UUID(first)  # parses as a valid UUID


def test_game_uid_changes_with_terms() -> None:
    assert derive_game_uid({"board_size": 7}, ["g"]) != derive_game_uid({"board_size": 8}, ["g"])


def test_game_uid_independent_of_key_order() -> None:
    """The uid depends only on term VALUES, not key order -- canonical_terms_json
    sorts keys, so two dicts built in different order must hash identically."""
    a = derive_game_uid({"board_size": 7, "num_games": 6}, ["g"])
    b = derive_game_uid({"num_games": 6, "board_size": 7}, ["g"])
    assert a == b


def test_terms_from_shared_config_excludes_non_negotiated_fields() -> None:
    """Regression test for the documented cross-team defect: the game_uid must
    be a function of the negotiated terms, not of unrelated config sections
    (schema_version, agreed_between, rate limiter minimums, ...)."""
    shared = load_shared_config(FIXTURES / "valid_shared_game.json")
    terms = terms_from_shared_config(shared)
    assert terms["board_size"] == 7
    assert terms["num_games"] == 6
    assert "schema_version" not in terms
    assert "agreed_between" not in terms
    assert "rate_limiter_gatekeeper" not in terms


def test_terms_from_shared_config_uses_reference_key_names() -> None:
    """Signed bytes are the reference implementation's projection, not our
    config file's own on-disk vocabulary (grid_size, map_area, ...)."""
    shared = load_shared_config(FIXTURES / "valid_shared_game.json")
    terms = terms_from_shared_config(shared)
    assert set(terms) == {
        "board_size",
        "thief_start",
        "cop_start",
        "axis_origin_corner",
        "axis_start_index",
        "setting",
        "hint_max_words",
        "barriers_max",
        "max_steps",
        "emit_intensity",
        "decay_per_step",
        "smell_grid_size",
        "num_games",
    }


def test_terms_from_shared_config_omits_min_center_intensity_when_unset() -> None:
    """The fixture config hasn't negotiated this extension, so it stays out
    of the signed terms -- optional per-pairing, not a blanket inclusion."""
    shared = load_shared_config(FIXTURES / "valid_shared_game.json")
    terms = terms_from_shared_config(shared)
    assert "min_center_intensity" not in terms


def test_terms_from_shared_config_includes_min_center_intensity_when_negotiated() -> None:
    """The real config (moamteam, 2026-08-17) has negotiated it, so it must
    be part of the signed terms -- either in both signatures or neither."""
    shared = load_shared_config(
        Path(__file__).resolve().parents[2] / "config" / "police" / "game.json"
    )
    terms = terms_from_shared_config(shared)
    assert terms["min_center_intensity"] == 0.5


def test_canonical_terms_json_is_compact_sorted_utf8() -> None:
    assert canonical_terms_json({"b": 1, "a": "אני"}) == '{"a":"אני","b":1}'

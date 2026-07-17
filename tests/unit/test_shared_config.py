"""Tests for loading and validating the shared game.json constitution."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_peer.shared.config_loader import load_shared_config, sha256_hex
from police_peer.shared.config_validation import is_league_series_ready
from police_peer.shared.errors import ConfigError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REAL_CONFIG = Path(__file__).resolve().parents[2] / "config" / "police" / "game.json"
EXPECTED_REAL_CONFIG_SHA256 = "5336607ef7f6cd786830b3a0640d4e2defbf1a96724fec498498017ca935c541"


def test_valid_shared_config_loads() -> None:
    config = load_shared_config(FIXTURES / "valid_shared_game.json")
    assert config.board_and_agents.grid_size == 7
    assert config.movement_and_barriers.max_barriers == 14
    assert config.network_and_league.num_games == 6


def test_invalid_movement_diagonal_rejected() -> None:
    with pytest.raises(ConfigError, match="move_set"):
        load_shared_config(FIXTURES / "invalid_movement_diagonal.json")


def test_invalid_board_size_rejected() -> None:
    with pytest.raises(ConfigError, match="grid_size"):
        load_shared_config(FIXTURES / "invalid_board_size.json")


def test_invalid_minimum_barriers_rejected() -> None:
    with pytest.raises(ConfigError, match="max_barriers"):
        load_shared_config(FIXTURES / "invalid_minimum_barriers.json")


def test_missing_field_rejected() -> None:
    with pytest.raises(ConfigError, match="scoring"):
        load_shared_config(FIXTURES / "missing_field_scoring.json")


def test_missing_file_rejected() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_shared_config(FIXTURES / "does_not_exist.json")


def test_smoke_fixture_uses_one_game() -> None:
    config = load_shared_config(FIXTURES / "valid_smoke_one_game.json")
    assert config.network_and_league.num_games == 1
    assert is_league_series_ready(config.network_and_league) is False


def test_league_config_uses_six_games() -> None:
    config = load_shared_config(REAL_CONFIG)
    assert config.network_and_league.num_games == 6
    assert is_league_series_ready(config.network_and_league) is True


def test_real_config_sha256_matches_expected() -> None:
    """Self-check: catches accidental drift without importing the sibling repo."""
    assert sha256_hex(REAL_CONFIG) == EXPECTED_REAL_CONFIG_SHA256


def test_pheromone_min_center_intensity_not_present() -> None:
    """The unverified reference-repo extension must not appear in our own config."""
    import json

    raw = json.loads(REAL_CONFIG.read_bytes())
    assert "pheromone_min_center_intensity" not in raw.get("pheromones", {})

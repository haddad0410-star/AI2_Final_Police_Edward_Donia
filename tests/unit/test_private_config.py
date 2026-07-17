"""Tests for loading the private game.toml and rejecting shared-field overrides."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_peer.shared.config_loader import load_private_config
from police_peer.shared.errors import ConfigError, PrivateOverrideError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REAL_PRIVATE_CONFIG = Path(__file__).resolve().parents[2] / "config" / "police" / "game.toml"


def test_valid_private_config_loads() -> None:
    config = load_private_config(FIXTURES / "valid_private_game.toml")
    assert config.game.group_id == "edward-donia"
    assert config.network.my_port == 8901
    assert config.trash_talk.provider == "template"
    assert config.email.mode == "disabled"


def test_private_override_attempt_rejected() -> None:
    with pytest.raises(PrivateOverrideError, match="board_and_agents"):
        load_private_config(FIXTURES / "private_override_attempt.toml")


def test_missing_private_file_rejected() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_private_config(FIXTURES / "does_not_exist.toml")


def test_real_private_config_loads_and_has_no_override() -> None:
    config = load_private_config(REAL_PRIVATE_CONFIG)
    assert config.game.group_id == "edward-donia"
    assert config.network.my_port == 8901
    assert config.email.recipient == "rmisegal+uoh26finalgame@gmail.com"
    assert config.email.mode == "disabled"

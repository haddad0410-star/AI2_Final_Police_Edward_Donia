"""Batch 3, Task 5: strategy profile / private-config validation --
import path, class inheritance, missing class, invalid weight, unknown key,
unsafe value."""

from __future__ import annotations

import pytest

from police_peer.shared.errors import ConfigError
from police_peer.shared.private_config import PrivateGameConfig
from police_peer.strategy.belief_cutoff_config import weights_from_dict
from police_peer.strategy.loader import StrategyLoadError, load_police_brain

_BASE = {
    "game": {"group_name": "g", "group_id": "g", "members": [], "repos": {}},
    "network": {"my_port": 8901, "opponent_url": "http://127.0.0.1:8902/mcp"},
}


def test_missing_class_raises_strategy_load_error() -> None:
    with pytest.raises(StrategyLoadError):
        load_police_brain("police_peer.strategy.baseline_police_brain:DoesNotExist")


def test_wrong_role_class_rejected() -> None:
    """A class that is not a PoliceBrainBase subclass must be rejected --
    the practical 'wrong role' check for a single-role loader."""
    with pytest.raises(StrategyLoadError):
        load_police_brain("police_peer.domain.roles:Role")


def test_bad_import_path_format_rejected() -> None:
    with pytest.raises(StrategyLoadError):
        load_police_brain("not_a_valid_reference")


def test_invalid_weight_value_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        weights_from_dict({"totally_bogus_weight": 1.0})


def test_unsafe_non_numeric_weight_value_rejected_at_config_load() -> None:
    data = {
        **_BASE,
        "strategy": {"profile": "experiment", "weights": {"expected_distance": "rm -rf /"}},
    }
    with pytest.raises(ConfigError, match="numeric"):
        PrivateGameConfig.from_dict(data)


def test_unknown_profile_name_rejected() -> None:
    data = {**_BASE, "strategy": {"profile": "not_a_real_profile"}}
    with pytest.raises(ConfigError, match="unknown strategy profile"):
        PrivateGameConfig.from_dict(data)


def test_baseline_profile_is_the_default() -> None:
    private = PrivateGameConfig.from_dict(_BASE)
    assert private.strategy.profile == "baseline"
    assert private.strategy.weights == {}


def test_advanced_profile_loads_with_default_weights() -> None:
    data = {
        **_BASE,
        "strategy": {
            "profile": "advanced",
            "police_class": "police_peer.strategy.belief_cutoff_police_brain:BeliefCutoffPoliceBrain",
        },
    }
    private = PrivateGameConfig.from_dict(data)
    assert private.strategy.profile == "advanced"
    brain = load_police_brain(private.strategy.police_class)
    assert type(brain).__name__ == "BeliefCutoffPoliceBrain"


def test_experiment_profile_applies_weight_overrides() -> None:
    data = {
        **_BASE,
        "strategy": {
            "profile": "experiment",
            "police_class": "police_peer.strategy.belief_cutoff_police_brain:BeliefCutoffPoliceBrain",
            "weights": {"expected_distance": 3.5},
        },
    }
    private = PrivateGameConfig.from_dict(data)
    weights = weights_from_dict(private.strategy.weights)
    brain = load_police_brain(private.strategy.police_class, weights=weights)
    assert brain._weights.expected_distance == 3.5


def test_baseline_class_ignores_weights_argument_safely() -> None:
    """Passing weights to a class with no such constructor parameter must
    never raise -- BaselinePoliceBrain is instantiated with no arguments."""
    weights = weights_from_dict({"expected_distance": 9.0})
    brain = load_police_brain(
        "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain", weights=weights
    )
    assert type(brain).__name__ == "BaselinePoliceBrain"

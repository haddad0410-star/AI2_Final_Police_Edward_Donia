"""Generic optional-field tolerance for `pheromone_min_center_intensity` (a
documented, non-binding reference-repo addition -- risk_register.md risk #2),
not an opponent-specific hack. Proves: existing configs still load unchanged,
an opponent's exact file carrying this extra field loads, the field is
optional, and malformed values are rejected.
"""

from __future__ import annotations

import copy

import pytest

from police_peer.shared.config_models import SharedGameConfig
from police_peer.shared.errors import ConfigError

_BASE: dict = {
    "schema_version": "1.0",
    "agreed_between": ["ed%do111"],
    "board_and_agents": {
        "grid_size": 7,
        "num_agents": 2,
        "thief_start": [3, 3],
        "cop_start": [0, 0],
        "axis_origin_corner": "top-left",
        "axis_start_index": 0,
    },
    "world": {"map_area": "New York", "hint_max_words": 15},
    "movement_and_barriers": {
        "move_set": ["N", "S", "E", "W", "STAY"],
        "max_barriers": 14,
        "max_moves": 35,
        "survival_threshold": 35,
    },
    "scoring": {
        "capture_cop": 20,
        "capture_thief": 5,
        "survival_cop": 5,
        "survival_thief": 10,
        "tie_score": 2,
        "technical_loss": 0,
    },
    "pheromones": {
        "pheromone_center_intensity": 0.9,
        "pheromone_decay": 0.1,
        "pheromone_grid_size": 5,
    },
    "network_and_league": {
        "response_timeout_sec": 30,
        "watchdog_timeout_sec": 60,
        "num_games": 6,
        "diversity_reward": 10,
        "min_games_to_pass": 2,
        "max_games_per_team": 10,
        "token_budget_per_series": 200000,
    },
    "rate_limiter_gatekeeper": {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    },
}


def test_a_existing_config_without_extension_still_loads() -> None:
    cfg = SharedGameConfig.from_dict(copy.deepcopy(_BASE))
    assert cfg.pheromones.pheromone_center_intensity == 0.9
    assert not hasattr(cfg.pheromones, "pheromone_min_center_intensity")


def test_b_opponent_file_with_extension_loads() -> None:
    data = copy.deepcopy(_BASE)
    data["pheromones"]["pheromone_min_center_intensity"] = 0.5
    cfg = SharedGameConfig.from_dict(data)
    assert cfg.pheromones.pheromone_center_intensity == 0.9
    assert cfg.pheromones.pheromone_decay == 0.1
    assert cfg.pheromones.pheromone_grid_size == 5


def test_c_extension_field_is_optional() -> None:
    data = copy.deepcopy(_BASE)
    assert "pheromone_min_center_intensity" not in data["pheromones"]
    cfg = SharedGameConfig.from_dict(data)
    assert cfg.pheromones.pheromone_center_intensity == 0.9


@pytest.mark.parametrize(
    "bad_value",
    [-0.1, "0.5", None, float("nan"), float("inf"), True, [0.5]],
)
def test_d_malformed_extension_values_rejected(bad_value: object) -> None:
    data = copy.deepcopy(_BASE)
    data["pheromones"]["pheromone_min_center_intensity"] = bad_value
    with pytest.raises(ConfigError, match="pheromone_min_center_intensity"):
        SharedGameConfig.from_dict(data)


def test_extension_never_required_in_baseline() -> None:
    """The real active config must never carry this extension -- it is not
    a binding Appendix F value, and this test guards against it silently
    creeping into our own baseline."""
    import json
    from pathlib import Path

    real = json.loads(
        (Path(__file__).resolve().parents[2] / "config" / "police" / "game.json").read_text()
    )
    assert "pheromone_min_center_intensity" not in real["pheromones"]

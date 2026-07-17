"""Validation rules for the shared game.json constitution.

Each `status` from Appendix F's own status-definitions (printed p.139, visually
verified) maps to a concrete rule here:

- constant  -> value must equal the Appendix F example exactly.
- minimum   -> value must be >= the Appendix F example.
- negotiable -> any value is structurally valid (semantic agreement is a
  runtime/negotiation concern, not a loader concern).

`num_games` is deliberately NOT enforced as a hard constant here even though
Appendix F Table 18 lists it as constant=6: a local single-sub-game smoke-test
fixture (integration_lab/config_fixtures/game_smoke_1.json) legitimately uses
num_games=1 and must still load successfully. League-readiness (num_games==6)
is checked separately by `is_league_series_ready`, not by this loader.
"""

from __future__ import annotations

from police_peer.shared.config_sections import (
    BoardAndAgents,
    MovementAndBarriers,
    NetworkAndLeague,
    Pheromones,
    RateLimiterGatekeeper,
    Scoring,
)
from police_peer.shared.errors import ConfigError

EXPECTED_MOVE_SET = frozenset({"N", "S", "E", "W", "STAY"})
LEAGUE_NUM_GAMES = 6


def validate_board_and_agents(section: BoardAndAgents) -> None:
    if not isinstance(section.grid_size, int) or section.grid_size < 7:
        raise ConfigError(f"grid_size must be an int >= 7 (minimum), got {section.grid_size!r}")
    if section.num_agents != 2:
        raise ConfigError(f"num_agents is constant=2, got {section.num_agents!r}")


def validate_movement_and_barriers(section: MovementAndBarriers) -> None:
    move_set = set(section.move_set)
    if move_set != EXPECTED_MOVE_SET:
        raise ConfigError(
            f"move_set is constant={sorted(EXPECTED_MOVE_SET)} (no diagonals), "
            f"got {sorted(move_set)}"
        )
    if section.max_barriers < 14:
        raise ConfigError(f"max_barriers must be >= 14 (minimum), got {section.max_barriers!r}")
    if section.max_moves < 35:
        raise ConfigError(f"max_moves must be >= 35 (minimum), got {section.max_moves!r}")
    if section.survival_threshold < 35:
        raise ConfigError(
            f"survival_threshold must be >= 35 (minimum), got {section.survival_threshold!r}"
        )


def validate_scoring(section: Scoring) -> None:
    expected = {
        "capture_cop": 20,
        "capture_thief": 5,
        "survival_cop": 5,
        "survival_thief": 10,
        "tie_score": 2,
        "technical_loss": 0,
    }
    for field, value in expected.items():
        actual = getattr(section, field)
        if actual != value:
            raise ConfigError(f"scoring.{field} is constant={value}, got {actual!r}")


def validate_pheromones(section: Pheromones) -> None:
    if section.pheromone_center_intensity != 0.9:
        raise ConfigError(
            "pheromone_center_intensity is constant=0.9, got "
            f"{section.pheromone_center_intensity!r}"
        )
    if section.pheromone_decay != 0.10:
        raise ConfigError(f"pheromone_decay is constant=0.10, got {section.pheromone_decay!r}")
    if section.pheromone_grid_size != 5:
        raise ConfigError(f"pheromone_grid_size is constant=5, got {section.pheromone_grid_size!r}")


def validate_network_and_league(section: NetworkAndLeague) -> None:
    if not isinstance(section.num_games, int) or section.num_games < 1:
        raise ConfigError(f"num_games must be a positive int, got {section.num_games!r}")
    if section.diversity_reward != 10:
        raise ConfigError(f"diversity_reward is constant=10, got {section.diversity_reward!r}")
    if section.min_games_to_pass != 2:
        raise ConfigError(f"min_games_to_pass is constant=2, got {section.min_games_to_pass!r}")
    if section.max_games_per_team != 10:
        raise ConfigError(f"max_games_per_team is constant=10, got {section.max_games_per_team!r}")


def validate_rate_limiter_gatekeeper(section: RateLimiterGatekeeper) -> None:
    minimums = {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    for field, minimum in minimums.items():
        actual = getattr(section, field)
        if actual < minimum:
            raise ConfigError(
                f"rate_limiter_gatekeeper.{field} must be >= {minimum} (minimum), got {actual!r}"
            )


def is_league_series_ready(network_and_league: NetworkAndLeague) -> bool:
    """True only if num_games matches the binding league constant (6)."""
    return network_and_league.num_games == LEAGUE_NUM_GAMES

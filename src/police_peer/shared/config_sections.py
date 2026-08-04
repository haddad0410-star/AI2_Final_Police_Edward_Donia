"""Immutable dataclasses for each section of the shared game.json constitution.

Field names mirror _post4b_supplementary_evidence/audit/binding_parameters.json exactly, one
dataclass per Appendix F table. No validation logic lives here; see
config_validation.py for the rules each section must satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardAndAgents:
    """Appendix F Table 13: board geometry and starting positions."""

    grid_size: int
    num_agents: int
    thief_start: tuple[int, int]
    cop_start: tuple[int, int]
    axis_origin_corner: str
    axis_start_index: int


@dataclass(frozen=True, slots=True)
class World:
    """Appendix F Table 14: verbal-hint world parameters."""

    map_area: str
    hint_max_words: int


@dataclass(frozen=True, slots=True)
class MovementAndBarriers:
    """Appendix F Table 15: movement set and barrier/step limits."""

    move_set: tuple[str, ...]
    max_barriers: int
    max_moves: int
    survival_threshold: int


@dataclass(frozen=True, slots=True)
class Scoring:
    """Appendix F Table 17: scoring constants."""

    capture_cop: int
    capture_thief: int
    survival_cop: int
    survival_thief: int
    tie_score: int
    technical_loss: int


@dataclass(frozen=True, slots=True)
class Pheromones:
    """Appendix F Table 16: scent emission/decay constants."""

    pheromone_center_intensity: float
    pheromone_decay: float
    pheromone_grid_size: int


@dataclass(frozen=True, slots=True)
class NetworkAndLeague:
    """Appendix F Table 18: league/series parameters."""

    response_timeout_sec: int
    watchdog_timeout_sec: int
    num_games: int
    diversity_reward: int
    min_games_to_pass: int
    max_games_per_team: int
    token_budget_per_series: int


@dataclass(frozen=True, slots=True)
class RateLimiterGatekeeper:
    """Appendix F Table 19: shared rate-limit minimums."""

    requests_per_minute: int
    concurrent_requests: int
    retry_backoff_sec: int
    max_retries: int
    queue_depth: int

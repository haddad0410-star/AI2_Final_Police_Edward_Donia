"""The immutable, validated SharedGameConfig aggregate ("the constitution").

Built from a raw dict (as parsed from game.json). Keys starting with "_" are
documentation/comment fields (a convention used throughout our draft configs)
and are ignored here, never treated as data.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.shared.config_sections import (
    BoardAndAgents,
    MovementAndBarriers,
    NetworkAndLeague,
    Pheromones,
    RateLimiterGatekeeper,
    Scoring,
    World,
)
from police_peer.shared.config_validation import (
    validate_board_and_agents,
    validate_movement_and_barriers,
    validate_network_and_league,
    validate_pheromones,
    validate_rate_limiter_gatekeeper,
    validate_scoring,
)
from police_peer.shared.errors import ConfigError

#: Top-level table names that belong exclusively to the SHARED constitution.
#: A private game.toml must never define any of these -- see PrivateOverrideError.
SHARED_TABLE_KEYS = frozenset(
    {
        "board_and_agents",
        "world",
        "movement_and_barriers",
        "scoring",
        "pheromones",
        "network_and_league",
        "rate_limiter_gatekeeper",
    }
)

_REQUIRED_KEYS = frozenset({"schema_version", "agreed_between", *SHARED_TABLE_KEYS})


def _clean(section: dict) -> dict:
    """Drop comment/documentation keys (leading underscore) before construction."""
    return {k: v for k, v in section.items() if not k.startswith("_")}


def _require(data: dict, key: str) -> dict:
    try:
        value = data[key]
    except KeyError as exc:
        raise ConfigError(f"missing required shared config section: {key!r}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"shared config section {key!r} must be an object")
    return _clean(value)


@dataclass(frozen=True, slots=True)
class SharedGameConfig:
    """The fully parsed and validated shared game.json constitution."""

    schema_version: str
    agreed_between: tuple[str, ...]
    board_and_agents: BoardAndAgents
    world: World
    movement_and_barriers: MovementAndBarriers
    scoring: Scoring
    pheromones: Pheromones
    network_and_league: NetworkAndLeague
    rate_limiter_gatekeeper: RateLimiterGatekeeper

    @classmethod
    def from_dict(cls, data: dict) -> SharedGameConfig:
        missing = _REQUIRED_KEYS - data.keys()
        if missing:
            raise ConfigError(f"missing required shared config keys: {sorted(missing)}")

        board = BoardAndAgents(**_require(data, "board_and_agents"))
        world = World(**_require(data, "world"))
        movement = MovementAndBarriers(**_require(data, "movement_and_barriers"))
        scoring = Scoring(**_require(data, "scoring"))
        pheromones = Pheromones(**_require(data, "pheromones"))
        league = NetworkAndLeague(**_require(data, "network_and_league"))
        rate_limits = RateLimiterGatekeeper(**_require(data, "rate_limiter_gatekeeper"))

        # Normalize tuple types (JSON gives lists) before validation.
        board = BoardAndAgents(
            grid_size=board.grid_size,
            num_agents=board.num_agents,
            thief_start=tuple(board.thief_start),
            cop_start=tuple(board.cop_start),
            axis_origin_corner=board.axis_origin_corner,
            axis_start_index=board.axis_start_index,
        )
        movement = MovementAndBarriers(
            move_set=tuple(movement.move_set),
            max_barriers=movement.max_barriers,
            max_moves=movement.max_moves,
            survival_threshold=movement.survival_threshold,
        )

        validate_board_and_agents(board)
        validate_movement_and_barriers(movement)
        validate_scoring(scoring)
        validate_pheromones(pheromones)
        validate_network_and_league(league)
        validate_rate_limiter_gatekeeper(rate_limits)

        return cls(
            schema_version=str(data["schema_version"]),
            agreed_between=tuple(data["agreed_between"]),
            board_and_agents=board,
            world=world,
            movement_and_barriers=movement,
            scoring=scoring,
            pheromones=pheromones,
            network_and_league=league,
            rate_limiter_gatekeeper=rate_limits,
        )

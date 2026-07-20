"""Immutable dataclasses for the PRIVATE, per-peer game.toml.

Nothing here is negotiated with the opponent; every field is local setup only.
See config_models.SHARED_TABLE_KEYS for the table names this file must never
define (enforced in config_loader.load_private_config).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from police_peer.shared.errors import ConfigError


@dataclass(frozen=True, slots=True)
class GameIdentity:
    group_name: str
    group_id: str
    sub_game_number: int
    members: tuple[str, ...]
    repos: dict[str, str]


@dataclass(frozen=True, slots=True)
class NetworkPrivate:
    my_port: int
    opponent_url: str
    turn_timeout_seconds: int


@dataclass(frozen=True, slots=True)
class TrashTalkConfig:
    provider: str = "template"


#: Documented private strategy profiles (Batch 3, Task 5) -- "baseline" and
#: "advanced" select the class default weights; "experiment" additionally
#: carries a [strategy.weights] override table. The profile NAME itself is
#: local documentation only; the authoritative, audited value is always
#: `police_class` (also recorded verbatim in the Step-0 declaration).
KNOWN_PROFILES = frozenset({"baseline", "advanced", "experiment"})


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Private, never-negotiated brain selection (``package.module:ClassName``)."""

    police_class: str = "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain"
    profile: str = "baseline"
    weights: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlayConfig:
    """Private RNG seed for league-mode tie-breaks; never shared or negotiated."""

    seed: int = 0


@dataclass(frozen=True, slots=True)
class EmailConfig:
    recipient: str = ""
    mode: str = "disabled"
    credentials_dir_env_var: str = "GMAIL_CREDENTIALS_DIR"


@dataclass(frozen=True, slots=True)
class PrivateGameConfig:
    """The fully parsed private game.toml for one peer."""

    version: str
    game: GameIdentity
    network: NetworkPrivate
    trash_talk: TrashTalkConfig
    email: EmailConfig
    strategy: StrategyConfig
    play: PlayConfig

    @classmethod
    def from_dict(cls, data: dict) -> PrivateGameConfig:
        try:
            game_raw = data["game"]
            network_raw = data["network"]
        except KeyError as exc:
            raise ConfigError(f"missing required private config table: {exc}") from exc

        game = GameIdentity(
            group_name=game_raw["group_name"],
            group_id=game_raw["group_id"],
            sub_game_number=int(game_raw.get("sub_game_number", 1)),
            members=tuple(game_raw.get("members", ())),
            repos=dict(game_raw.get("repos", {})),
        )
        network = NetworkPrivate(
            my_port=int(network_raw["my_port"]),
            opponent_url=network_raw["opponent_url"],
            turn_timeout_seconds=int(network_raw.get("turn_timeout_seconds", 180)),
        )
        trash_talk = TrashTalkConfig(
            provider=data.get("trash_talk", {}).get("provider", "template")
        )
        email_raw = data.get("email", {})
        email = EmailConfig(
            recipient=email_raw.get("recipient", ""),
            mode=email_raw.get("mode", "disabled"),
            credentials_dir_env_var=email_raw.get(
                "credentials_dir_env_var", "GMAIL_CREDENTIALS_DIR"
            ),
        )
        strategy_raw = data.get("strategy", {})
        profile = strategy_raw.get("profile", "baseline")
        if profile not in KNOWN_PROFILES:
            raise ConfigError(
                f"unknown strategy profile {profile!r}; expected one of {sorted(KNOWN_PROFILES)}"
            )
        weights_raw = strategy_raw.get("weights", {})
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in weights_raw.values()
        ):
            raise ConfigError("strategy.weights values must all be numeric")
        strategy = StrategyConfig(
            police_class=strategy_raw.get(
                "police_class", "police_peer.strategy.baseline_police_brain:BaselinePoliceBrain"
            ),
            profile=profile,
            weights=dict(weights_raw),
        )
        play = PlayConfig(seed=int(data.get("play", {}).get("seed", 0)))
        return cls(
            version=str(data.get("version", "0.0.0")),
            game=game,
            network=network,
            trash_talk=trash_talk,
            email=email,
            strategy=strategy,
            play=play,
        )

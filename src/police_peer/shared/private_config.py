"""Immutable dataclasses for the PRIVATE, per-peer game.toml.

Nothing here is negotiated with the opponent; every field is local setup only.
See config_models.SHARED_TABLE_KEYS for the table names this file must never
define (enforced in config_loader.load_private_config).
"""

from __future__ import annotations

from dataclasses import dataclass

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
        return cls(
            version=str(data.get("version", "0.0.0")),
            game=game,
            network=network,
            trash_talk=trash_talk,
            email=email,
        )

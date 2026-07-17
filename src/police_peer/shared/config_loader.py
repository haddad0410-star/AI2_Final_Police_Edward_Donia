"""Load and validate the three configuration files each peer reads at startup.

- game.json   -> SharedGameConfig  (the byte-identical, signed constitution)
- game.toml   -> PrivateGameConfig (this peer's own private setup only)
- rate_limits.json -> RateLimitsConfig (private Gatekeeper settings)
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from police_peer.shared.config_models import SHARED_TABLE_KEYS, SharedGameConfig
from police_peer.shared.errors import ConfigError, PrivateOverrideError
from police_peer.shared.private_config import PrivateGameConfig
from police_peer.shared.rate_limits_model import RateLimitsConfig


def read_raw_bytes(path: Path) -> bytes:
    """Read a config file's raw bytes, failing clearly if it does not exist."""
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    return path.read_bytes()


def sha256_hex(path: Path) -> str:
    """SHA-256 of a config file's raw bytes, as a lowercase hex string."""
    return hashlib.sha256(read_raw_bytes(path)).hexdigest()


def load_shared_config(path: Path) -> SharedGameConfig:
    """Load, parse, and validate the shared game.json constitution."""
    raw = read_raw_bytes(path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in shared config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"shared config {path} must be a JSON object")
    return SharedGameConfig.from_dict(data)


def _assert_no_shared_table_override(private_data: dict, path: Path) -> None:
    forbidden = SHARED_TABLE_KEYS & private_data.keys()
    if forbidden:
        raise PrivateOverrideError(
            f"private config {path} attempts to override binding shared field(s): "
            f"{sorted(forbidden)} -- these belong exclusively in game.json"
        )


def load_private_config(path: Path) -> PrivateGameConfig:
    """Load, parse, and validate the private game.toml (rejects shared overrides)."""
    raw = read_raw_bytes(path)
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in private config {path}: {exc}") from exc
    _assert_no_shared_table_override(data, path)
    return PrivateGameConfig.from_dict(data)


def load_rate_limits(path: Path) -> RateLimitsConfig:
    """Load, parse, and validate the private rate_limits.json."""
    raw = read_raw_bytes(path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in rate limits config {path}: {exc}") from exc
    cleaned = {k: v for k, v in data.items() if not k.startswith("_") and k != "gmail"}
    return RateLimitsConfig.from_dict(cleaned)

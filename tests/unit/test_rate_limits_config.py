"""Tests for loading the private rate_limits.json Gatekeeper config."""

from __future__ import annotations

from pathlib import Path

import pytest

from police_peer.shared.config_loader import load_rate_limits
from police_peer.shared.errors import ConfigError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REAL_RATE_LIMITS = Path(__file__).resolve().parents[2] / "config" / "police" / "rate_limits.json"


def test_valid_rate_limits_loads() -> None:
    config = load_rate_limits(FIXTURES / "valid_rate_limits.json")
    assert config.requests_per_minute == 30
    assert config.queue_depth == 100


def test_missing_rate_limits_file_rejected() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_rate_limits(FIXTURES / "does_not_exist.json")


def test_real_rate_limits_config_loads() -> None:
    config = load_rate_limits(REAL_RATE_LIMITS)
    assert config.requests_per_minute >= 30
    assert config.concurrent_requests >= 2
    assert config.retry_backoff_sec >= 5
    assert config.max_retries >= 3
    assert config.queue_depth >= 100

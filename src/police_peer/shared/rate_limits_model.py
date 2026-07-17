"""Immutable dataclass for the private rate_limits.json (Gatekeeper config)."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.shared.errors import ConfigError


@dataclass(frozen=True, slots=True)
class RateLimitsConfig:
    """Local Gatekeeper rate-limit settings, built from Appendix F Table 19 minimums."""

    requests_per_minute: int
    concurrent_requests: int
    retry_backoff_sec: int
    max_retries: int
    queue_depth: int

    @classmethod
    def from_dict(cls, data: dict) -> RateLimitsConfig:
        required = (
            "requests_per_minute",
            "concurrent_requests",
            "retry_backoff_sec",
            "max_retries",
            "queue_depth",
        )
        missing = [key for key in required if key not in data]
        if missing:
            raise ConfigError(f"rate_limits.json missing required keys: {missing}")
        return cls(**{key: data[key] for key in required})

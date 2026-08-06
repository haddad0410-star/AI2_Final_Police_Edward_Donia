"""Gate A1 correction: ``_build_pacer`` is only constructed when an
opponent token is present (i.e. the opponent runs ``--public``) -- ordinary
local/non-public self-play never builds a pacer, so its behavior is
provably byte-for-byte unaffected (test requirement #12). Also proves the
overload error/retry path never discloses a token value anywhere (#11)."""

from __future__ import annotations

from pathlib import Path

from police_peer.infrastructure.mcp_rate_limit_middleware import McpOverloadError
from police_peer.sdk.game_runner import _build_pacer

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"


def test_no_opponent_token_means_no_pacer() -> None:
    assert _build_pacer(None, CONFIG_DIR) is None


def test_opponent_token_present_builds_a_real_pacer() -> None:
    pacer = _build_pacer("some-opponent-token", CONFIG_DIR)
    assert pacer is not None
    assert pacer._config.requests_per_minute == 30  # the real committed config


def test_overload_error_never_contains_a_token_value() -> None:
    token = "z" * 40
    exc = McpOverloadError("rate_limit_exceeded", retry_after_seconds=5.0)
    assert token not in str(exc)
    assert token not in repr(exc.error.data)

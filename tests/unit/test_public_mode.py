"""Gate A1: resolve_public_tokens / build_public_middleware -- fail-closed
token resolution, independent of any real server."""

from __future__ import annotations

import pytest

from police_peer.sdk.public_mode import PublicModeError, resolve_public_tokens


def test_non_public_mode_needs_no_token(monkeypatch) -> None:
    monkeypatch.delenv("PUBLIC_BIND_TOKEN", raising=False)
    assert resolve_public_tokens(False) == (None, None)


def test_public_mode_fails_closed_when_token_missing(monkeypatch) -> None:
    monkeypatch.delenv("PUBLIC_BIND_TOKEN", raising=False)
    with pytest.raises(PublicModeError):
        resolve_public_tokens(True)


def test_public_mode_fails_closed_when_token_blank(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BIND_TOKEN", "   ")
    with pytest.raises(PublicModeError):
        resolve_public_tokens(True)


def test_public_mode_accepts_a_real_token(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BIND_TOKEN", "e" * 40)
    monkeypatch.delenv("OPPONENT_MCP_TOKEN", raising=False)
    public_token, opponent_token = resolve_public_tokens(True)
    assert public_token == "e" * 40
    assert opponent_token is None


def test_public_mode_reads_opponent_token_when_present(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BIND_TOKEN", "e" * 40)
    monkeypatch.setenv("OPPONENT_MCP_TOKEN", "f" * 40)
    public_token, opponent_token = resolve_public_tokens(True)
    assert opponent_token == "f" * 40


def test_error_message_never_contains_a_token_value(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BIND_TOKEN", "")
    try:
        resolve_public_tokens(True)
        raise AssertionError("expected PublicModeError")
    except PublicModeError as exc:
        assert "PUBLIC_BIND_TOKEN" in str(exc)  # the field name, not a value

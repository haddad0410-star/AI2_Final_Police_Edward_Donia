"""Batch 4A Task 13: public-auth preparation tests (never starts a server,
never touches the network -- ``server_lifecycle.py``'s localhost-only
guard is unchanged and untested here since it's already covered
elsewhere)."""

from __future__ import annotations

import pytest

from police_peer.infrastructure.public_auth import (
    PublicAuthError,
    resolve_bind_token,
    verify_bearer_token,
)


def test_missing_token_env_var_fails_clearly() -> None:
    with pytest.raises(PublicAuthError, match="PUBLIC_BIND_TOKEN"):
        resolve_bind_token(env={})


def test_too_short_token_rejected() -> None:
    with pytest.raises(PublicAuthError, match="too short"):
        resolve_bind_token(env={"PUBLIC_BIND_TOKEN": "short"})


def test_valid_token_resolves() -> None:
    token = "a" * 40
    assert resolve_bind_token(env={"PUBLIC_BIND_TOKEN": token}) == token


def test_matching_token_verifies() -> None:
    token = "b" * 40
    assert verify_bearer_token(token, token) is True


def test_non_matching_token_rejected() -> None:
    assert verify_bearer_token("x" * 40, "y" * 40) is False


def test_missing_presented_token_rejected() -> None:
    assert verify_bearer_token(None, "z" * 40) is False


def test_token_never_appears_in_error_message() -> None:
    secret = "s3cr3t-token-value-should-never-leak-anywhere"
    try:
        resolve_bind_token(env={"PUBLIC_BIND_TOKEN": secret[:10]})
    except PublicAuthError as exc:
        assert secret not in str(exc)


def test_no_token_field_in_committed_config_files() -> None:
    """No JSON/TOML config file in this repo may contain a bind-token-like
    field name -- the token must live only in the environment. Falls back to
    a full filesystem scan when ``.git`` is absent (e.g. a clean-extracted
    review ZIP) -- never silently skipped."""
    from pathlib import Path

    from _repo_scan import repo_files

    repo_root = Path(__file__).resolve().parents[2]
    names = [n for n in repo_files(repo_root) if n.endswith((".json", ".toml"))]
    for name in names:
        content = (repo_root / name).read_text(encoding="utf-8", errors="ignore").lower()
        assert "public_bind_token" not in content, f"{name} must not contain a bind token"


def test_revocation_instructions_present_and_non_trivial() -> None:
    from police_peer.infrastructure.public_auth import revocation_instructions

    text = revocation_instructions()
    assert len(text) > 50
    assert "revoke" in text.lower()

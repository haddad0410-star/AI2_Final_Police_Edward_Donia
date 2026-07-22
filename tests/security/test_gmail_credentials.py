"""Batch 4A Task 10: Gmail credential isolation/security tests."""

from __future__ import annotations

import logging

import pytest

from police_peer.infrastructure.gmail_credentials import (
    REQUIRED_SCOPE,
    CredentialResolutionError,
    assert_scope_is_send_only,
    resolve_credential_paths,
)


def test_missing_env_var_fails_clearly() -> None:
    with pytest.raises(CredentialResolutionError, match="GOOGLE_OAUTH_CREDENTIAL_DIR"):
        resolve_credential_paths(env={})


def test_missing_external_directory_fails_clearly(tmp_path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(CredentialResolutionError, match="missing credentials file"):
        resolve_credential_paths(env={"GOOGLE_OAUTH_CREDENTIAL_DIR": str(missing)})


def test_missing_token_file_fails_clearly(tmp_path) -> None:
    (tmp_path / "credentials.json").write_text("{}")
    with pytest.raises(CredentialResolutionError, match="missing token file"):
        resolve_credential_paths(env={"GOOGLE_OAUTH_CREDENTIAL_DIR": str(tmp_path)})


def test_valid_directory_resolves(tmp_path) -> None:
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")
    paths = resolve_credential_paths(env={"GOOGLE_OAUTH_CREDENTIAL_DIR": str(tmp_path)})
    assert paths.credentials_path == tmp_path / "credentials.json"
    assert paths.token_path == tmp_path / "token.json"


def test_send_only_scope_accepted() -> None:
    assert_scope_is_send_only([REQUIRED_SCOPE])  # must not raise


def test_forbidden_broad_scope_rejected() -> None:
    with pytest.raises(CredentialResolutionError, match="forbidden broad Gmail scope"):
        assert_scope_is_send_only(["https://www.googleapis.com/auth/gmail.modify"])


def test_missing_required_scope_rejected() -> None:
    with pytest.raises(CredentialResolutionError, match="missing required scope"):
        assert_scope_is_send_only(["https://www.googleapis.com/auth/calendar"])


def test_compose_scope_rejected() -> None:
    with pytest.raises(CredentialResolutionError):
        assert_scope_is_send_only([REQUIRED_SCOPE, "https://www.googleapis.com/auth/gmail.compose"])


def test_full_mailbox_scope_rejected() -> None:
    with pytest.raises(CredentialResolutionError):
        assert_scope_is_send_only(["https://mail.google.com/"])


def test_no_credential_files_committed_in_repo() -> None:
    """credentials.json/token.json/client_secret* must never exist inside
    this repository, even outside git (a stray local file is still risky)."""
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for name in tracked:
        lowered = name.lower()
        assert "credentials.json" not in lowered
        assert "token.json" not in lowered
        assert not lowered.startswith("client_secret")


def test_credential_error_messages_never_contain_file_content(tmp_path) -> None:
    """A CredentialResolutionError's message must describe WHAT is wrong,
    never echo the file's own bytes -- even if a caller feeds a huge or
    secret-looking value in via the env dict."""
    secret_looking = "FAKE-SECRET-LOOKING-VALUE-FOR-TEST-ONLY-1234567890"
    (tmp_path / "credentials.json").write_text(secret_looking)
    try:
        resolve_credential_paths(env={"GOOGLE_OAUTH_CREDENTIAL_DIR": str(tmp_path)})
    except CredentialResolutionError as exc:
        assert secret_looking not in str(exc)


def test_no_credential_content_logged(tmp_path, caplog) -> None:
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text('{"token": "fake-token-value-for-test"}')
    with caplog.at_level(logging.DEBUG):
        resolve_credential_paths(env={"GOOGLE_OAUTH_CREDENTIAL_DIR": str(tmp_path)})
    assert "fake-token-value-for-test" not in caplog.text

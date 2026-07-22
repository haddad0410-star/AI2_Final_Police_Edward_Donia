"""Batch 4A Task 10: Gmail OAuth credential resolution.

``credentials.json``/``token.json`` must live OUTSIDE this repository,
resolved only via ``GOOGLE_OAUTH_CREDENTIAL_DIR``. This module never
prints, copies, base64-encodes, or logs file CONTENT -- only paths and
booleans. Dry-run mode never calls anything here; only ``--send`` does.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REQUIRED_SCOPE = "https://www.googleapis.com/auth/gmail.send"
_FORBIDDEN_BROAD_SCOPES = (
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://mail.google.com/",
)


class CredentialResolutionError(Exception):
    """Raised when credentials cannot be safely resolved -- never includes
    file content, only the path and a description of what's wrong."""


@dataclass(frozen=True, slots=True)
class CredentialPaths:
    credentials_path: Path
    token_path: Path


def resolve_credential_paths(env: dict | None = None) -> CredentialPaths:
    """Resolve, but do not open/parse, both files. Raises with a clear,
    content-free message if the env var or files are missing."""
    environ = env if env is not None else os.environ
    directory = environ.get("GOOGLE_OAUTH_CREDENTIAL_DIR")
    if not directory:
        raise CredentialResolutionError(
            "GOOGLE_OAUTH_CREDENTIAL_DIR is not set; --send requires it (dry-run does not)"
        )
    base = Path(directory)
    credentials_path = base / "credentials.json"
    token_path = base / "token.json"
    if not credentials_path.exists():
        raise CredentialResolutionError(f"missing credentials file at {credentials_path}")
    if not token_path.exists():
        raise CredentialResolutionError(f"missing token file at {token_path}")
    return CredentialPaths(credentials_path=credentials_path, token_path=token_path)


def assert_scope_is_send_only(scopes: list[str]) -> None:
    """Reject any credential whose granted scope set includes a broader
    Gmail permission than ``gmail.send`` -- least privilege, enforced in
    code, not just documented."""
    forbidden = [s for s in scopes if s in _FORBIDDEN_BROAD_SCOPES]
    if forbidden:
        raise CredentialResolutionError(f"forbidden broad Gmail scope(s) requested: {forbidden}")
    if REQUIRED_SCOPE not in scopes:
        raise CredentialResolutionError(f"missing required scope {REQUIRED_SCOPE!r}")

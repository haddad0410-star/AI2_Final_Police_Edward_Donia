"""Batch 4A Task 13: bearer-token auth for a FUTURE public deployment.

Preparation only -- this module is never wired into the live server this
batch (``infrastructure/server_lifecycle.py`` still hard-blocks any host
other than 127.0.0.1/localhost/::1; see its ``_ALLOWED_LOCAL_HOSTS``
guard, unchanged). No tunnel is started, no token is generated or
requested from a real provider, and no public endpoint is tested.

Token source: ``PUBLIC_BIND_TOKEN`` environment variable only -- never a
TOML/JSON config field (those are committed to the repo; a token must
never be). Never logged, never echoed back in an error message.
"""

from __future__ import annotations

import hmac
import os


class PublicAuthError(Exception):
    """Raised when public-mode auth cannot be established -- messages
    never include the actual token value, only what's missing/wrong."""


def resolve_bind_token(env: dict | None = None) -> str:
    environ = env if env is not None else os.environ
    token = environ.get("PUBLIC_BIND_TOKEN")
    if not token:
        raise PublicAuthError(
            "PUBLIC_BIND_TOKEN is not set; --public mode requires it (default localhost mode does not)"
        )
    if len(token) < 32:
        raise PublicAuthError(
            "PUBLIC_BIND_TOKEN is too short to be a real bearer token (min 32 chars)"
        )
    return token


def verify_bearer_token(presented: str | None, expected: str) -> bool:
    """Constant-time comparison -- a timing side-channel on token
    verification is exactly the kind of leak Ch.5.2's threat model warns
    about generally, so the same discipline applies here."""
    if presented is None:
        return False
    return hmac.compare_digest(presented, expected)


def revocation_instructions() -> str:
    return (
        "To revoke a leaked PUBLIC_BIND_TOKEN: (1) generate a new random "
        'token (e.g. `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`), '
        "(2) set PUBLIC_BIND_TOKEN to the new value in the environment "
        "used to launch the peer -- never in a committed file, "
        "(3) restart the peer process so the new token takes effect, "
        "(4) if a tunnel provider issued its own separate access token, "
        "revoke that token in the provider's own dashboard too."
    )

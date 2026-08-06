"""Gate A1: proves BearerAuthMiddleware's token check actually routes
through ``hmac.compare_digest`` (constant-time) rather than a plain ``==``
-- a timing measurement itself would be flaky in a test environment, so
this asserts the real comparison primitive is used, the same pattern
already established for ``infrastructure/public_auth.py``."""

from __future__ import annotations

import hmac
from unittest.mock import patch

from police_peer.infrastructure import auth_middleware as am

TOKEN = "a" * 40


def test_token_check_calls_hmac_compare_digest() -> None:
    with patch.object(am.hmac, "compare_digest", wraps=hmac.compare_digest) as spy:
        mw = am.BearerAuthMiddleware(None, expected_token=TOKEN)
        reason = mw._check({b"authorization": f"Bearer {TOKEN}".encode()})
    assert reason is None
    spy.assert_called_once_with(TOKEN, TOKEN)


def test_wrong_token_still_goes_through_compare_digest_not_short_circuited() -> None:
    with patch.object(am.hmac, "compare_digest", wraps=hmac.compare_digest) as spy:
        mw = am.BearerAuthMiddleware(None, expected_token=TOKEN)
        reason = mw._check({b"authorization": b"Bearer " + b"z" * 40})
    assert reason == "invalid_token"
    spy.assert_called_once()

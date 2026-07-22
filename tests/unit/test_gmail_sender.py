"""Batch 4A Task 9/10/11: Gmail sender tests. Always dry-run or a mocked
Gatekeeper/send_fn -- never a real Gmail API call.
"""

from __future__ import annotations

import asyncio

import pytest

from police_peer.domain.gmail_report_schema import MANDATORY_RECIPIENT
from police_peer.infrastructure.gmail_credentials import CredentialPaths
from police_peer.infrastructure.gmail_gatekeeper import Gatekeeper
from police_peer.infrastructure.gmail_sender import (
    RecipientMismatchError,
    dry_run,
    send,
)
from police_peer.shared.rate_limits_model import RateLimitsConfig

_REPORT = {
    "schema_version": "gmail-report/1",
    "recipient": MANDATORY_RECIPIENT,
    "game_id": "edward-donia",
    "game_uid": "abc-123",
    "config_sha256": "deadbeef" * 8,
}


def test_dry_run_never_touches_network(monkeypatch) -> None:
    def _boom(*a, **kw):
        raise AssertionError("dry-run must never open a socket")

    monkeypatch.setattr("socket.socket.connect", _boom)
    report = dry_run(_REPORT)
    assert report.would_send_to == MANDATORY_RECIPIENT
    assert report.body == _REPORT


def test_dry_run_recipient_is_mandatory_address() -> None:
    report = dry_run(_REPORT)
    assert report.would_send_to == "rmisegal+uoh26finalgame@gmail.com"


def test_dry_run_idempotency_key_stable() -> None:
    r1 = dry_run(_REPORT)
    r2 = dry_run(_REPORT)
    assert r1.idempotency_key == r2.idempotency_key


def test_send_rejects_recipient_mismatch(tmp_path) -> None:
    bad_report = {**_REPORT, "recipient": "someone-else@example.com"}
    creds = CredentialPaths(tmp_path / "credentials.json", tmp_path / "token.json")

    async def send_fn(message):
        return {"id": "1"}

    gk = Gatekeeper(
        RateLimitsConfig(
            requests_per_minute=5,
            concurrent_requests=1,
            retry_backoff_sec=0,
            max_retries=1,
            queue_depth=5,
        ),
        send_fn,
    )
    with pytest.raises(RecipientMismatchError):
        asyncio.run(send(bad_report, gk, creds, ["https://www.googleapis.com/auth/gmail.send"]))


def test_send_rejects_forbidden_scope_before_network(tmp_path) -> None:
    creds = CredentialPaths(tmp_path / "credentials.json", tmp_path / "token.json")
    called = {"n": 0}

    async def send_fn(message):
        called["n"] += 1
        return {"id": "1"}

    gk = Gatekeeper(
        RateLimitsConfig(
            requests_per_minute=5,
            concurrent_requests=1,
            retry_backoff_sec=0,
            max_retries=1,
            queue_depth=5,
        ),
        send_fn,
    )
    from police_peer.infrastructure.gmail_credentials import CredentialResolutionError

    with pytest.raises(CredentialResolutionError):
        asyncio.run(send(_REPORT, gk, creds, ["https://www.googleapis.com/auth/gmail.modify"]))
    assert called["n"] == 0  # never reached the network layer


def test_send_routes_through_gatekeeper(tmp_path) -> None:
    creds = CredentialPaths(tmp_path / "credentials.json", tmp_path / "token.json")
    called = {"n": 0}

    async def send_fn(message):
        called["n"] += 1
        assert "raw" in message
        return {"id": "1"}

    gk = Gatekeeper(
        RateLimitsConfig(
            requests_per_minute=5,
            concurrent_requests=1,
            retry_backoff_sec=0,
            max_retries=1,
            queue_depth=5,
        ),
        send_fn,
    )
    result = asyncio.run(send(_REPORT, gk, creds, ["https://www.googleapis.com/auth/gmail.send"]))
    assert result.ok is True
    assert called["n"] == 1

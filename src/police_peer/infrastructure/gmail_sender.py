"""Batch 4A Task 9/11: the Gmail send-only reporter. ``gmail.send`` scope
ONLY (no modify/compose/readonly) -- see ``gmail_credentials.py``. Default
mode is dry-run (no network, no OAuth); ``send`` requires an explicit flag
AND real credentials, and always routes through the Gatekeeper. No draft
mode: the book's least-privilege mandate excludes it (drafting needs a
broader scope than pure sending).
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from police_peer.domain.gmail_report_schema import MANDATORY_RECIPIENT
from police_peer.infrastructure.gmail_credentials import (
    REQUIRED_SCOPE,
    CredentialPaths,
    assert_scope_is_send_only,
)
from police_peer.infrastructure.gmail_gatekeeper import Gatekeeper, GatekeeperResult


class GmailClient(Protocol):
    """Real implementations wrap ``googleapiclient.discovery`` (lazy-
    imported, gmail-send extra only); tests always inject a mock."""

    async def send(self, raw_message_b64: str) -> dict: ...


@dataclass(frozen=True, slots=True)
class DryRunReport:
    would_send_to: str
    subject: str
    body: dict
    idempotency_key: str


class RecipientMismatchError(Exception):
    """Raised if a report's recipient ever diverges from the one mandatory,
    book-confirmed address -- a hard stop, never silently corrected."""


def _idempotency_key(report: dict) -> str:
    return f"{report.get('game_uid')}:{report.get('config_sha256')}"


def _assert_recipient(report: dict) -> None:
    recipient = report.get("recipient")
    if recipient != MANDATORY_RECIPIENT:
        raise RecipientMismatchError(f"report recipient {recipient!r} != {MANDATORY_RECIPIENT!r}")


def dry_run(report: dict) -> DryRunReport:
    """No network call, no OAuth -- always available, always safe."""
    return DryRunReport(
        would_send_to=MANDATORY_RECIPIENT,
        subject=f"[AI2 Final] {report.get('game_id')} / {report.get('game_uid')}",
        body=report,
        idempotency_key=_idempotency_key(report),
    )


def _mime_message(report: dict, subject: str) -> str:
    import json
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["To"] = MANDATORY_RECIPIENT
    msg["Subject"] = subject
    msg.set_content(json.dumps(report, indent=2))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


async def send(
    report: dict, gatekeeper: Gatekeeper, credentials: CredentialPaths, granted_scopes: list[str]
) -> GatekeeperResult:
    """Real send path -- always through the Gatekeeper, never direct.
    ``granted_scopes``/recipient must both be checked BEFORE any network call."""
    assert_scope_is_send_only(granted_scopes)
    _assert_recipient(report)
    _ = credentials  # resolved paths only; content is read inside build_real_client, never here
    plan = dry_run(report)
    return await gatekeeper.submit(
        {"raw": _mime_message(report, plan.subject)}, plan.idempotency_key
    )


def build_real_send_fn(credentials: CredentialPaths) -> Callable:
    """Lazy-imports the Google client libraries -- only reached if
    ``--send`` is actually used with the ``gmail-send`` extra installed.
    Never imported, never called, by dry-run mode or by the test suite."""

    def _factory():
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(credentials.token_path), [REQUIRED_SCOPE])
        service = build("gmail", "v1", credentials=creds)

        async def _send(message: dict) -> dict:
            return service.users().messages().send(userId="me", body=message).execute()

        return _send

    return _factory

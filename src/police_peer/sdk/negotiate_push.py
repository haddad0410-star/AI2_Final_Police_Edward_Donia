"""Best-effort pre-game handshake push (SPEC section 4).

Split out of ``game_runner.py`` (150-line limit): some opponents refuse to
accept real turns into a live series until a signed agreement has landed in
their negotiate inbox first -- our own ``negotiate`` tool never required
this, so nothing in the real match flow ever sent one until this module.
"""

from __future__ import annotations

import contextlib

from police_peer.infrastructure.mcp_client import call_negotiate
from police_peer.services.game_ids import build_signed_negotiate_message, terms_from_shared_config


async def push_negotiate(shared, private, opponent_url: str, role: str, opponent_token) -> None:
    """Send a signed negotiate; never raises. A failure here does not abort
    the series -- an opponent that doesn't require negotiate is unaffected,
    and a genuine no-show still fails honestly at the first real turn,
    unchanged."""
    message = build_signed_negotiate_message(
        terms_from_shared_config(shared),
        group_id=private.game.group_id,
        role=role,
        sub_game_number=private.game.sub_game_number,
        correlation_id=f"{private.game.group_id}-negotiate-{role}",
    )
    # Broad by design: an HTTP error status (rejected/malformed on the
    # opponent's side) surfaces as httpx.HTTPStatusError, not
    # PeerUnavailableError -- any failure here must not crash the series,
    # since this is only a best-effort side channel, never a hard requirement.
    with contextlib.suppress(Exception):
        await call_negotiate(opponent_url, message, timeout_seconds=15, token=opponent_token)

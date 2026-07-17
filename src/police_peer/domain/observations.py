"""Public information exchanged between peers, and what a peer locally observes.

A PublicTurnEnvelope is the shape of "what one peer's turn reveals publicly" --
it never contains a true position, only what the protocol legally makes public
(hint, scent trail, barrier declarations, capture-claim exchange).
"""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.domain.captures import CaptureClaim, CaptureResponse
from police_peer.domain.hints import Hint
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import ScentField


@dataclass(frozen=True, slots=True)
class PublicTurnEnvelope:
    """Everything one peer's turn reveals publicly -- and nothing more."""

    sender: Role
    step: int
    sub_game_number: int
    hint: Hint
    scent: ScentField
    timestamp: str
    barrier_placed: Position | None = None
    capture_claim: CaptureClaim | None = None
    claim_response: CaptureResponse | None = None
    win_claim: bool = False


@dataclass(frozen=True, slots=True)
class LocalObservation:
    """This peer's local record of one PublicTurnEnvelope received from the
    opponent, plus when (in this peer's own step counter) it arrived."""

    envelope: PublicTurnEnvelope
    received_at_step: int

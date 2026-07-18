"""The opponent-transport seam for the sub-game runtime.

The runtime never talks to the network directly; it drives an
:class:`OpponentTransport`. Production supplies an HTTP implementation; tests
supply an in-process fake (mocks are test-only). Crucially, an
:class:`OpponentReveal` carries ONLY public information -- the opponent's move,
hint, scent, any declared barrier, and an HONEST yes/no answer to our capture
claim -- never the opponent's true position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class OpponentReveal:
    """The opponent's public turn info, as legally received by this peer."""

    move: str | None
    hint: str
    scent_grid: tuple[tuple[float, ...], ...]
    barrier: tuple[int, int] | None = None
    claim_response: bool | None = None
    win_claim: bool = False


@dataclass(frozen=True, slots=True)
class TechnicalFailure:
    """Returned by a transport when the opponent is unreachable or malformed."""

    reason: str


@runtime_checkable
class OpponentTransport(Protocol):
    """One round-trip: deliver our commitment + reveal, receive the opponent's."""

    async def exchange_turn(
        self, commitment: dict, reveal: dict
    ) -> OpponentReveal | TechnicalFailure:
        """Send our sealed commitment then public reveal; return the opponent's reveal."""
        ...

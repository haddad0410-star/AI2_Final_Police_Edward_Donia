"""Typed sub-game outcomes for the runtime.

Every way a sub-game can end -- capture, survival, or a technical failure
(malformed opponent, deadline, watchdog) -- is an explicit value, never a hang.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import SealedRecord
from police_peer.services.subgame_state import RuntimeState


@dataclass(frozen=True, slots=True)
class SubGameRunResult:
    """The full result of running one sub-game to termination."""

    result: SubGameResult
    steps: int
    reason: str
    final_state: RuntimeState
    records: tuple[SealedRecord, ...] = field(default_factory=tuple)

    @property
    def is_technical_loss(self) -> bool:
        return self.result is SubGameResult.TECHNICAL_LOSS

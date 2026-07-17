"""The two roles in the game. A single peer process always plays exactly one."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """POLICE chases; THIEF evades. Each peer is permanently one of these."""

    POLICE = "police"
    THIEF = "thief"

    def opponent(self) -> Role:
        """The other role -- never used to access the opponent's true state."""
        return Role.THIEF if self is Role.POLICE else Role.POLICE

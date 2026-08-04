"""The free natural-language hint each peer may attach to its turn.

Per the book (Ch.5.3.1): the hint text may lie, but the sender must honestly
declare whether it is lying via `intent` -- the declaration itself must always
be truthful (Appendix E rule 22: false intent declaration is disqualifying;
`intent` is a sealed commit-reveal field, so any post-hoc tampering is
detected by the final audit, implemented in `domain/crypto/audit.py`, not
here).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HintIntent(StrEnum):
    """Whether the sender is declaring their hint text truthful or a lie."""

    TRUTH = "truth"
    LIE = "lie"


@dataclass(frozen=True, slots=True)
class Hint:
    """A verbal hint, word-limited by the shared config's hint_max_words."""

    text: str
    intent: HintIntent

    def word_count(self) -> int:
        return len(self.text.split())

    def within_word_limit(self, max_words: int) -> bool:
        return self.word_count() <= max_words

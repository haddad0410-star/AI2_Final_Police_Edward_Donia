"""Offline, zero-token template hint provider (Batch 2, Phase 8).

Renders short natural-language banter consistent with a given ``intent`` flag
(truthful vs deceptive). It has NO access to positions, moves, or cryptographic
fields -- it only produces generic district/street/route language, so the clean
seam between deceptive hint text and always-truthful physical/crypto fields is
preserved structurally. No coordinates, no JSON, no network, no LLM tokens.
"""

from __future__ import annotations

import random

from police_peer.domain.hints import Hint, HintIntent

#: Generic region words substituted into templates for variety (never a coordinate).
REGIONS: tuple[str, ...] = ("northern", "southern", "eastern", "western", "central")

#: Truthful-leaning phrasings (still generic; carry intent=TRUTH).
_TRUTHFUL: tuple[str, ...] = (
    "The {region} avenues look like a sensible route right now.",
    "I am drifting toward the {region} district this turn.",
    "The {region} streets feel like the natural way to go.",
    "My path seems to lean into the {region} quarter for now.",
    "Heading roughly along the {region} boulevards feels right.",
    "The {region} lanes are where I expect to be soon.",
)

#: Deceptive-leaning phrasings (still generic; carry intent=LIE).
_DECEPTIVE: tuple[str, ...] = (
    "The {region} district is far too exposed for me today.",
    "I would never risk the crowded {region} streets now.",
    "Forget the {region} lanes; they are a dead end for me.",
    "The {region} quarter holds nothing useful this turn.",
    "I am steering well clear of the {region} boulevards.",
    "The {region} avenues feel like a trap I will avoid.",
)

#: Fixed Hebrew hints, included to exercise Unicode robustness end-to-end.
_HEBREW: tuple[str, ...] = (
    "אני נע לכיוון הרובע הצפוני",
    "הרחובות המרכזיים חשופים מדי כעת",
)


class TemplateHintProvider:
    """Deterministic (given an RNG) offline hint generator."""

    def __init__(self, max_words: int = 15) -> None:
        self._max_words = max_words

    def generate(
        self,
        intent: HintIntent,
        rng: random.Random,
        use_hebrew: bool = False,
        region: str | None = None,
    ) -> Hint:
        """Render one word-limited hint consistent with ``intent``.

        ``region`` (a cardinal word), when given, flavours the text -- the
        caller decides whether it is the true or a false region, per
        ``intent``; this provider has no access to positions itself.
        Truncates defensively so the returned hint always respects
        ``max_words``, even if a future template were edited to be longer.
        """
        if use_hebrew:
            text = rng.choice(_HEBREW)
        else:
            pool = _TRUTHFUL if intent is HintIntent.TRUTH else _DECEPTIVE
            chosen_region = region if region in REGIONS else rng.choice(REGIONS)
            text = rng.choice(pool).format(region=chosen_region)
        words = text.split()
        if len(words) > self._max_words:
            text = " ".join(words[: self._max_words])
        return Hint(text=text, intent=intent)

    def template_count(self) -> int:
        """Total distinct templates available (for coverage/inspection)."""
        return len(_TRUTHFUL) + len(_DECEPTIVE) + len(_HEBREW)

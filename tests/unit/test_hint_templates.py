"""Phase 8: template hint provider -- word limit, no coordinates, determinism."""

from __future__ import annotations

import random
import re
import sys

from police_peer.domain.hints import HintIntent
from police_peer.strategy.hint_templates import TemplateHintProvider

#: Any pair of numbers separated by a comma (with optional parens) reads as a coordinate.
_COORD_PATTERN = re.compile(r"\(?\s*\d+\s*,\s*\d+\s*\)?")
#: A lone number could still be a smuggled coordinate component.
_DIGIT_PATTERN = re.compile(r"\d")


def test_word_limit_enforced() -> None:
    provider = TemplateHintProvider(max_words=15)
    rng = random.Random(0)
    for _ in range(200):
        for intent in (HintIntent.TRUTH, HintIntent.LIE):
            hint = provider.generate(intent, rng)
            assert hint.word_count() <= 15
            assert hint.within_word_limit(15)


def test_custom_word_limit_truncates() -> None:
    provider = TemplateHintProvider(max_words=3)
    hint = provider.generate(HintIntent.TRUTH, random.Random(1))
    assert hint.word_count() <= 3


def test_no_coordinates_present() -> None:
    provider = TemplateHintProvider()
    rng = random.Random(7)
    for _ in range(500):
        for intent in (HintIntent.TRUTH, HintIntent.LIE):
            text = provider.generate(intent, rng).text
            assert not _COORD_PATTERN.search(text), text
            assert not _DIGIT_PATTERN.search(text), text  # no digits at all


def test_truthful_selection_carries_truth_intent() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.TRUTH, random.Random(3))
    assert hint.intent is HintIntent.TRUTH


def test_deceptive_selection_carries_lie_intent() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.LIE, random.Random(3))
    assert hint.intent is HintIntent.LIE


def test_truthful_and_deceptive_pools_differ() -> None:
    provider = TemplateHintProvider()
    truths = {provider.generate(HintIntent.TRUTH, random.Random(s)).text for s in range(30)}
    lies = {provider.generate(HintIntent.LIE, random.Random(s)).text for s in range(30)}
    assert truths.isdisjoint(lies)


def test_deterministic_in_test_mode() -> None:
    provider = TemplateHintProvider()
    a = provider.generate(HintIntent.TRUTH, random.Random(99)).text
    b = provider.generate(HintIntent.TRUTH, random.Random(99)).text
    assert a == b


def test_unicode_hebrew_hint_round_trips() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.TRUTH, random.Random(0), use_hebrew=True)
    assert hint.text  # non-empty
    assert hint.text.encode("utf-8").decode("utf-8") == hint.text
    assert not _DIGIT_PATTERN.search(hint.text)


def test_at_least_six_distinct_templates() -> None:
    assert TemplateHintProvider().template_count() >= 6


def test_no_network_or_llm_imports_in_module() -> None:
    """The hint module must not depend on any network/LLM client library."""
    module = sys.modules["police_peer.strategy.hint_templates"]
    source = module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    for banned in ("import requests", "import httpx", "import anthropic", "urllib.request"):
        assert banned not in text, banned

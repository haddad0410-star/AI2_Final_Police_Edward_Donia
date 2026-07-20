"""Batch 3.5 Task 5: hint transport + trust repair coverage."""

from __future__ import annotations

import random

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.crypto import SealedTurnPayload, compute_commit_hash
from police_peer.domain.crypto.sealing import digest_scent_grid
from police_peer.domain.hint_region import parse_region_from_hint, region_cells
from police_peer.domain.hints import HintIntent
from police_peer.domain.positions import Position
from police_peer.domain.scent import empty_scent_field
from police_peer.services.belief_update import advance_belief
from police_peer.services.capture_resolution import ingest_opponent_reveal
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentReveal
from police_peer.strategy.hint_templates import TemplateHintProvider

GRID = 7


def _state() -> RuntimeState:
    return RuntimeState(
        role=None,
        position=Position(0, 0),
        visited=frozenset(),
        board=Board(grid_size=GRID),
        barriers_remaining=14,
        belief=uniform_prior(GRID),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )


def test_truthful_hint_boosts_probability_in_expected_region() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.TRUTH, random.Random(0), region="northern")
    region = region_cells(parse_region_from_hint(hint.text), GRID)
    state = _state()
    state = ingest_opponent_reveal(
        state, OpponentReveal(move="N", hint=hint.text, scent_grid=None, barrier=None)
    )
    before_mass = sum(state.belief.grid[p.row][p.col] for p in region)
    after = advance_belief(state)
    after_mass = sum(after.belief.grid[p.row][p.col] for p in region)
    assert after_mass > before_mass


def test_deceptive_hint_is_physically_legal_text() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.LIE, random.Random(1), region="southern")
    assert len(hint.text.split()) <= 15
    assert not any(ch.isdigit() for ch in hint.text)
    region_word = parse_region_from_hint(hint.text)
    assert region_word in ("northern", "southern", "eastern", "western", "central")


def test_impossible_hint_cannot_override_barriers() -> None:
    board = Board(grid_size=GRID)
    for r in range(GRID):
        board = board.with_barrier(Position(r, 0))  # wall off the whole western column
    state = _state()
    state = RuntimeState(
        role=None,
        position=Position(3, 3),
        visited=frozenset(),
        board=board,
        barriers_remaining=14,
        belief=uniform_prior(GRID, board.barriers),
        own_scent=empty_scent_field(GRID),
        received_scent=empty_scent_field(GRID),
        step=0,
        sub_game_number=1,
    )
    state = ingest_opponent_reveal(
        state,
        OpponentReveal(
            move="N", hint="the western avenues look promising", scent_grid=None, barrier=None
        ),
    )
    after = advance_belief(state)
    for r in range(GRID):
        assert after.belief.grid[r][0] == 0.0  # barrier cells stay impossible regardless of hint


def test_repeated_contradictions_reduce_trust() -> None:
    """Direct unit coverage of the trust-update rule (Batch 3.5 Task 5): an
    evidence-contradicting hint (entropy rises when applied) must reduce
    trust, and repeated contradictions must compound the reduction."""
    from police_peer.services.belief_update import _update_hint_trust

    trust = 0.5
    history = [trust]
    for _ in range(3):
        trust = _update_hint_trust(trust, entropy_before=2.0, entropy_after=2.5)
        history.append(trust)
    assert history[1] < history[0]
    assert history[-1] < history[1]  # compounds further down, not a one-shot drop
    assert history[-1] >= 0.05  # bounded floor, never driven to exactly zero


def test_agreeing_hint_increases_trust() -> None:
    from police_peer.services.belief_update import _update_hint_trust

    updated = _update_hint_trust(0.5, entropy_before=2.5, entropy_after=2.0)
    assert updated > 0.5


def test_no_coordinates_in_generated_hints() -> None:
    provider = TemplateHintProvider()
    rng = random.Random(7)
    for _ in range(50):
        hint = provider.generate(rng.choice([HintIntent.TRUTH, HintIntent.LIE]), rng)
        assert not any(ch.isdigit() for ch in hint.text)


def test_word_cap_enforced() -> None:
    provider = TemplateHintProvider(max_words=15)
    rng = random.Random(3)
    for _ in range(50):
        hint = provider.generate(rng.choice([HintIntent.TRUTH, HintIntent.LIE]), rng)
        assert len(hint.text.split()) <= 15


def test_unicode_hebrew_hint_round_trips() -> None:
    provider = TemplateHintProvider()
    hint = provider.generate(HintIntent.TRUTH, random.Random(0), use_hebrew=True)
    payload = SealedTurnPayload(
        step=0,
        role="police",
        sub_game_number=1,
        state={"position": [0, 0]},
        move="N",
        barrier_placed=None,
        intent=hint.intent.value,
        hint=hint.text,
        scent_digest=digest_scent_grid(empty_scent_field(GRID).grid),
        scent_grid=empty_scent_field(GRID).grid,
        capture_claim=None,
        claim_response=None,
        win_claim=False,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce="b" * 64,
    )
    reveal = payload.public_reveal_dict()
    assert reveal["hint"] == hint.text


def test_hint_covered_by_commitment() -> None:
    def payload(hint_text: str) -> SealedTurnPayload:
        return SealedTurnPayload(
            step=0,
            role="police",
            sub_game_number=1,
            state={"position": [0, 0]},
            move="N",
            barrier_placed=None,
            intent="truth",
            hint=hint_text,
            scent_digest=digest_scent_grid(empty_scent_field(GRID).grid),
            scent_grid=empty_scent_field(GRID).grid,
            capture_claim=None,
            claim_response=None,
            win_claim=False,
            timestamp="2026-07-18T00:00:00+00:00",
            nonce="c" * 64,
        )

    assert compute_commit_hash(payload("a")) != compute_commit_hash(payload("b"))


def test_intent_verdict_not_revealed_early() -> None:
    payload = SealedTurnPayload(
        step=0,
        role="police",
        sub_game_number=1,
        state={"position": [0, 0]},
        move="N",
        barrier_placed=None,
        intent="lie",
        hint="the eastern quarter looks promising",
        scent_digest=digest_scent_grid(empty_scent_field(GRID).grid),
        scent_grid=empty_scent_field(GRID).grid,
        capture_claim=None,
        claim_response=None,
        win_claim=False,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce="d" * 64,
    )
    reveal = payload.public_reveal_dict()
    assert "intent" not in reveal
    assert "nonce" not in reveal
    full = payload.to_canonical_dict()
    assert full["intent"] == "lie"  # still sealed/committed, just not disclosed early


def test_no_llm_dependency_in_hint_provider() -> None:
    import police_peer.strategy.hint_templates as module

    source = module.__file__
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    for banned in ("openai", "anthropic", "requests", "httpx", "urllib"):
        assert banned not in text.lower()


def test_unparseable_hint_is_neutral_missing_evidence() -> None:
    state = _state()
    state = ingest_opponent_reveal(
        state,
        OpponentReveal(move="N", hint="static noise on the line", scent_grid=None, barrier=None),
    )
    assert state.hint_region is None

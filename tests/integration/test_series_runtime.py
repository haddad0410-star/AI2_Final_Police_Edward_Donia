"""Phase 10: six-sub-game series aggregation, agreement, and termination."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.state_machine import PeerState
from police_peer.services.series_runtime import run_series
from police_peer.services.series_scoring import (
    SubGameRecord,
    aggregate,
    resolve_final_agreement,
)
from police_peer.services.transport import OpponentReveal, TechnicalFailure
from police_peer.shared.config_loader import load_private_config, load_shared_config, sha256_hex

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"
GRID = 7
ZERO = tuple(tuple(0.0 for _ in range(GRID)) for _ in range(GRID))


def _load():
    return (
        load_shared_config(CONFIG_DIR / "game.json"),
        load_private_config(CONFIG_DIR / "game.toml"),
        sha256_hex(CONFIG_DIR / "game.json"),
    )


class QuickCaptureTransport:
    """Confirms our capture claim on the first exchange (1-step sub-games)."""

    async def exchange_turn(self, commitment, reveal):
        return OpponentReveal("STAY", "caught", ZERO, claim_response=True)


class FailingTransport:
    async def exchange_turn(self, commitment, reveal):
        return TechnicalFailure("malformed")


def _run(transport_provider, *, num_games=None, their_totals=None):
    shared, private, sha = _load()
    return asyncio.run(
        run_series(
            shared,
            private,
            transport_provider,
            game_uid="uid",
            config_sha256=sha,
            num_games=num_games,
            their_totals=their_totals,
            rng=random.Random(1),
        )
    )


def test_full_six_game_series_aggregates() -> None:
    result = _run(lambda i: QuickCaptureTransport())
    assert len(result.sub_games) == 6
    assert all(r.result is SubGameResult.CAPTURE for r in result.sub_games)
    assert result.final_state is PeerState.SERIES_COMPLETE
    # 6 captures: police 6*20=120, thief 6*5=30.
    assert aggregate(result.sub_games) == (120, 30)


def test_smoke_single_game_selection() -> None:
    result = _run(lambda i: QuickCaptureTransport(), num_games=1)
    assert len(result.sub_games) == 1
    assert result.final_state is PeerState.SERIES_COMPLETE


def test_disagreement_zeroes_both() -> None:
    result = _run(lambda i: QuickCaptureTransport(), their_totals=(999, 0))
    assert result.agreement.agreed is False
    assert result.agreement.status == "disputed_zeroed"
    assert (result.agreement.police_total, result.agreement.thief_total) == (0, 0)


def test_matching_totals_agree() -> None:
    result = _run(lambda i: QuickCaptureTransport(), their_totals=(120, 30))
    assert result.agreement.agreed is True
    assert result.agreement.status == "agreed"


def test_technical_loss_ends_series() -> None:
    result = _run(lambda i: FailingTransport())
    assert result.terminated_reason == "technical_loss_ended_series"
    assert result.final_state is PeerState.ERROR
    assert len(result.sub_games) == 1
    assert result.sub_games[0].result is SubGameResult.TECHNICAL_LOSS


def test_resolve_final_agreement_pure() -> None:
    assert resolve_final_agreement(10, 5, 10, 5).agreed is True
    zeroed = resolve_final_agreement(10, 5, 9, 5)
    assert zeroed.agreed is False
    assert (zeroed.police_total, zeroed.thief_total) == (0, 0)
    unverified = resolve_final_agreement(10, 5, None, None)
    assert unverified.status == "unverified_self_play"


def test_aggregate_sums_records() -> None:
    records = [
        SubGameRecord(1, SubGameResult.CAPTURE, 20, 5, 3, True),
        SubGameRecord(2, SubGameResult.SURVIVAL, 5, 10, 35, True),
    ]
    assert aggregate(records) == (25, 15)

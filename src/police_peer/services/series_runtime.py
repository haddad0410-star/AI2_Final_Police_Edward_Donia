"""Six-sub-game local series runtime (Batch 2, Phase 10).

Runs ``num_games`` sub-games (default 6 from the shared config -- the smoke
fixture's ``num_games=1`` is only reachable via an explicit CLI ``--smoke``
flag), resetting state per sub-game, scoring and auditing each, then performing
the final mutual agreement. Roles are FIXED as police for the whole series (no
role alternation). A technical loss ends the series immediately (ERROR is
terminal). Immutable per-sub-game records are appended, never overwritten.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from police_peer.domain.crypto import audit_records
from police_peer.domain.scoring import score_sub_game
from police_peer.domain.state_machine import EventKind, PeerState, PeerStateMachine, TransitionEvent
from police_peer.services.series_scoring import (
    FinalAgreement,
    SubGameRecord,
    aggregate,
    resolve_final_agreement,
)
from police_peer.services.subgame_runtime import (
    advance_to_signed,
    await_opponent_ready,
    build_context,
)
from police_peer.services.transport import OpponentTransport
from police_peer.services.turn_loop import run_sub_game
from police_peer.shared.config_models import SharedGameConfig
from police_peer.shared.private_config import PrivateGameConfig

E = EventKind


@dataclass(frozen=True, slots=True)
class SeriesResult:
    """The whole-series outcome: per-sub-game records + final agreement."""

    sub_games: tuple[SubGameRecord, ...]
    agreement: FinalAgreement
    terminated_reason: str
    final_state: PeerState
    records_by_sub_game: tuple[tuple, ...] = field(default_factory=tuple)


async def run_series(
    shared: SharedGameConfig,
    private: PrivateGameConfig,
    transport_provider: Callable[[int], OpponentTransport],
    *,
    game_uid: str,
    config_sha256: str,
    num_games: int | None = None,
    their_totals: tuple[int, int] | None = None,
    machine: PeerStateMachine | None = None,
    rng: random.Random | None = None,
    opponent_url: str | None = None,
) -> SeriesResult:
    """Run a full series and return its aggregated, mutually-audited result."""
    games = num_games if num_games is not None else shared.network_and_league.num_games
    machine = machine if machine is not None else PeerStateMachine()
    rng = rng if rng is not None else random.Random(private.play.seed)
    advance_to_signed(machine)
    await await_opponent_ready(opponent_url)
    records: list[SubGameRecord] = []
    sealed_by_game: list[tuple] = []
    reason = "completed"
    for index in range(games):
        _enter_sub_game(machine, index)
        context = build_context(
            shared,
            private,
            transport_provider(index),
            machine=machine,
            game_uid=game_uid,
            config_sha256=config_sha256,
            sub_game_number=index + 1,
            rng=rng,
        )
        outcome = await run_sub_game(context)
        police, thief = score_sub_game(outcome.result, shared.scoring)
        audit_ok = audit_records(outcome.records).ok
        records.append(
            SubGameRecord(index + 1, outcome.result, police, thief, outcome.steps, audit_ok)
        )
        sealed_by_game.append(outcome.records)
        if outcome.is_technical_loss:
            reason = "technical_loss_ended_series"
            break
        machine.require(TransitionEvent.of(E.BEGIN_AUDIT))
    agreement = _finalize(machine, records, their_totals, reason)
    return SeriesResult(tuple(records), agreement, reason, machine.state, tuple(sealed_by_game))


def _enter_sub_game(machine: PeerStateMachine, index: int) -> None:
    if index == 0:
        machine.require(TransitionEvent.of(E.START_SUB_GAME))
    else:
        machine.require(TransitionEvent.of(E.NEXT_SUB_GAME, more_sub_games=True))


def _finalize(
    machine: PeerStateMachine,
    records: list[SubGameRecord],
    their_totals: tuple[int, int] | None,
    reason: str,
) -> FinalAgreement:
    our_police, our_thief = aggregate(records)
    if reason != "completed":
        return FinalAgreement(False, "technical_loss", 0, 0)
    their_police, their_thief = their_totals if their_totals is not None else (None, None)
    agreement = resolve_final_agreement(our_police, our_thief, their_police, their_thief)
    machine.require(TransitionEvent.of(E.COMPLETE_SERIES, more_sub_games=False))
    return agreement

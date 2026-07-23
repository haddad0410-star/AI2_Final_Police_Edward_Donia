"""Batch 4A Task 3: thin publish-helpers so ``turn_loop.py`` stays under the
150-meaningful-line cap. Pure construction + ``gui_sink.publish`` calls,
no control flow -- keeps the event-shape decisions in one place."""

from __future__ import annotations

from police_peer.domain.belief_model import BeliefMap
from police_peer.domain.belief_model import entropy as _entropy
from police_peer.domain.belief_model import top_k as _top_k
from police_peer.services import gui_sink
from police_peer.services.gui_events import (
    BeliefSnapshot,
    SubGameResultEvent,
    TurnDecisionEvent,
    TurnExchangeEvent,
)


def belief_snapshot(belief: BeliefMap) -> BeliefSnapshot:
    return BeliefSnapshot(
        grid_size=belief.grid_size,
        heatmap=belief.grid,
        entropy_bits=_entropy(belief),
        top_k=tuple((p.row, p.col, round(prob, 8)) for p, prob in _top_k(belief, 5)),
    )


def decision(
    *,
    sub_game_number,
    step,
    position_before,
    position_after,
    visited_count,
    action,
    barrier,
    barriers_remaining,
    belief,
    hint_text,
    strategy_class,
    latency,
) -> None:
    gui_sink.publish(
        TurnDecisionEvent(
            sub_game_number=sub_game_number,
            step=step,
            own_position_before=(position_before.row, position_before.col),
            own_position_after=(position_after.row, position_after.col),
            own_visited_count=visited_count,
            action_selected=action,
            barrier_placed=(barrier.row, barrier.col) if barrier else None,
            barriers_remaining=barriers_remaining,
            belief=belief_snapshot(belief),
            outgoing_hint_text=hint_text,
            strategy_class=strategy_class,
            decision_latency_seconds=latency,
        )
    )


def exchange_ok(state, hint_text: str, config_sha256: str, machine_state: str) -> None:
    # A returned OpponentReveal means all four real substeps completed.
    _exchange(
        state,
        True,
        True,
        True,
        True,
        "reveal",
        hint_text,
        state.board.barriers,
        config_sha256,
        machine_state,
    )


def exchange_failed(state, config_sha256: str, machine_state: str, failure=None) -> None:
    # ``failure`` carries the REAL per-substep progress made before the
    # fault (see infrastructure.http_transport); no progress info (a
    # non-exchange runtime fault) means none of the three is claimed.
    commit_sent = getattr(failure, "commit_sent", False)
    commit_acked = getattr(failure, "commit_acked", False)
    reveal_sent = getattr(failure, "reveal_sent", False)
    _exchange(
        state,
        commit_sent,
        commit_acked,
        reveal_sent,
        False,
        "technical_failure",
        "",
        (),
        config_sha256,
        machine_state,
    )


def _exchange(
    state,
    commit_sent: bool,
    ack_received: bool,
    reveal_sent: bool,
    reveal_received: bool,
    message_type: str,
    hint_text: str,
    barriers,
    config_sha256: str,
    machine_state: str,
) -> None:
    gui_sink.publish(
        TurnExchangeEvent(
            sub_game_number=state.sub_game_number,
            step=state.step,
            commit_sent=commit_sent,
            ack_received=ack_received,
            reveal_sent=reveal_sent,
            reveal_received=reveal_received,
            last_message_type=message_type,
            received_hint_text=hint_text,
            barriers=tuple((b.row, b.col) for b in barriers),
            config_sha256_prefix=config_sha256[:8],
            machine_state=machine_state,
        )
    )


def result_for(state, outcome: str, reason: str, records: list, machine_state: str) -> None:
    gui_sink.publish(
        SubGameResultEvent(
            sub_game_number=state.sub_game_number,
            result=outcome,
            reason=reason,
            steps=len(records),
            police_score=None,
            thief_score=None,
            machine_state=machine_state,
        )
    )

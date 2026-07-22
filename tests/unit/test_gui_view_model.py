"""Batch 4A Task 5: headless tests for the live-GUI view model. No display,
no Tkinter import anywhere in this file -- the view model/reducer is pure
data, testable exactly like any other domain module.
"""

from __future__ import annotations

from police_peer.gui.event_queue import GuiEventBus
from police_peer.gui.view_model import LiveViewModel, fold
from police_peer.services.gui_events import (
    AuditEvent,
    BeliefSnapshot,
    ConnectionEvent,
    SubGameResultEvent,
    TurnDecisionEvent,
    TurnExchangeEvent,
)

_BELIEF = BeliefSnapshot(
    grid_size=7,
    heatmap=tuple(tuple(1 / 49 for _ in range(7)) for _ in range(7)),
    entropy_bits=5.6,
    top_k=((0, 0, 0.1), (1, 1, 0.05)),
)


def _decision(sub_game=1, step=0, pos=(0, 0)) -> TurnDecisionEvent:
    return TurnDecisionEvent(
        sub_game_number=sub_game,
        step=step,
        own_position_before=(0, 0),
        own_position_after=pos,
        own_visited_count=step + 1,
        action_selected="E",
        barrier_placed=None,
        barriers_remaining=14,
        belief=_BELIEF,
        outgoing_hint_text="the eastern quarter looks promising",
        strategy_class="police_peer.strategy.baseline_police_brain.BaselinePoliceBrain",
        decision_latency_seconds=0.001,
    )


def _exchange(sub_game=1, step=0, ok=True, barriers=()) -> TurnExchangeEvent:
    return TurnExchangeEvent(
        sub_game_number=sub_game,
        step=step,
        commit_sent=True,
        ack_received=ok,
        reveal_sent=ok,
        reveal_received=ok,
        last_message_type="reveal" if ok else "technical_failure",
        received_hint_text="the western quarter" if ok else "",
        barriers=barriers,
        config_sha256_prefix="abc12345",
        machine_state="TURN_VERIFIED",
    )


def test_own_position_visible() -> None:
    model = fold(LiveViewModel(), _decision(pos=(2, 3)))
    assert model.own_position == (2, 3)
    assert (2, 3) in model.own_path


def test_belief_heatmap_present() -> None:
    model = fold(LiveViewModel(), _decision())
    assert model.belief is not None
    assert model.belief.grid_size == 7
    assert model.belief.entropy_bits == 5.6


def test_barriers_present() -> None:
    model = fold(LiveViewModel(), _exchange(barriers=((1, 1), (2, 2))))
    assert model.public_barriers == ((1, 1), (2, 2))


def test_hint_text_present() -> None:
    model = fold(LiveViewModel(), _decision())
    assert "eastern" in model.latest_sent_hint
    model2 = fold(model, _exchange())
    assert "western" in model2.latest_received_hint


def test_hidden_hint_intent() -> None:
    model = fold(LiveViewModel(), _decision())
    for f in model.__dataclass_fields__:
        assert "intent" not in f.lower()


def test_hidden_nonce() -> None:
    model = fold(LiveViewModel(), _exchange())
    for f in model.__dataclass_fields__:
        assert "nonce" not in f.lower()


def test_state_machine_status_update() -> None:
    model = fold(LiveViewModel(), _exchange())
    assert model.state_machine_state == "TURN_VERIFIED"


def test_sub_game_reset() -> None:
    model = fold(LiveViewModel(), _decision(sub_game=1, step=0, pos=(1, 1)))
    model = fold(model, _decision(sub_game=1, step=1, pos=(1, 2)))
    assert len(model.own_path) == 2
    model = fold(
        model,
        SubGameResultEvent(
            sub_game_number=1,
            result="capture",
            reason="capture confirmed",
            steps=2,
            police_score=None,
            thief_score=None,
            machine_state="AUDITING",
        ),
    )
    assert model.banner == "capture"
    model = fold(model, _decision(sub_game=2, step=0, pos=(0, 0)))
    assert model.own_path == ((0, 0),)
    assert model.banner == "playing"


def test_event_ordering() -> None:
    model = LiveViewModel()
    for step in range(3):
        model = fold(model, _decision(step=step, pos=(0, step)))
    assert model.own_path == ((0, 0), (0, 1), (0, 2))
    assert model.step == 2


def test_duplicate_event_idempotency() -> None:
    event = _decision(step=0, pos=(0, 1))
    model = fold(LiveViewModel(), event)
    model_again = fold(model, event)
    assert model_again.own_path == model.own_path
    assert model_again is model or model_again.own_path == ((0, 1),)


def test_disconnected_banner() -> None:
    model = fold(LiveViewModel(), ConnectionEvent(status="disconnected", opponent_url="http://x"))
    assert model.banner == "disconnected"


def test_timeout_banner() -> None:
    model = fold(LiveViewModel(), ConnectionEvent(status="timeout", opponent_url="http://x"))
    assert model.banner == "timeout"


def test_capture_banner() -> None:
    event = SubGameResultEvent(
        sub_game_number=1,
        result="capture",
        reason="capture confirmed",
        steps=5,
        police_score=None,
        thief_score=None,
        machine_state="AUDITING",
    )
    model = fold(LiveViewModel(), event)
    assert model.banner == "capture"


def test_survival_banner() -> None:
    event = SubGameResultEvent(
        sub_game_number=1,
        result="survival",
        reason="thief survived move limit",
        steps=35,
        police_score=None,
        thief_score=None,
        machine_state="AUDITING",
    )
    model = fold(LiveViewModel(), event)
    assert model.banner == "survival"


def test_technical_loss_banner() -> None:
    event = SubGameResultEvent(
        sub_game_number=1,
        result="technical_loss",
        reason="peer unreachable",
        steps=1,
        police_score=None,
        thief_score=None,
        machine_state="ERROR",
    )
    model = fold(LiveViewModel(), event)
    assert model.banner == "technical_loss"


def test_audit_event_folds() -> None:
    model = fold(LiveViewModel(), AuditEvent(sub_game_number=1, verdict="VERIFIED", reason="ok"))
    assert model.audit_verdict == "VERIFIED"


def test_unknown_event_ignored() -> None:
    model = LiveViewModel()
    assert fold(model, object()) == model


def test_event_bus_is_nonblocking_and_thread_safe() -> None:
    """Task 3/5: producer.publish() never blocks the consumer thread --
    queue.Queue is thread-safe by construction; drain() is non-blocking."""
    bus = GuiEventBus()
    assert bus.drain() == []
    bus.publish(_decision())
    bus.publish(_exchange())
    items = bus.drain()
    assert len(items) == 2


def test_no_direct_domain_mutation_via_fold() -> None:
    """fold() never mutates its inputs -- both the model and the event are
    frozen dataclasses, and fold always returns a NEW model."""
    model = LiveViewModel()
    event = _decision()
    new_model = fold(model, event)
    assert model.own_position is None
    assert new_model is not model

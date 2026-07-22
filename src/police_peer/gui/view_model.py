"""Batch 4A Task 3/5: the live-GUI view model. Pure data + a pure reducer
(``fold``) -- no Tkinter import anywhere in this module, so it is fully
testable without a display (Task 5). ``gui/`` only ever CONSUMES the event
types defined in ``services/gui_events.py``; it never calls into FastMCP,
never mutates domain state, and never selects a move.

Every field here is restricted to what Task 4 allows a live GUI to show:
this peer's own truth, public evidence, and this peer's own local belief.
There is deliberately no field anywhere in this module (or in
``services/gui_events.py``) named or shaped like an opponent true position
-- enforced by ``tests/unit/test_gui_no_opponent_leak.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

from police_peer.services.gui_events import (
    AuditEvent,
    BeliefSnapshot,
    ConnectionEvent,
    StateMachineEvent,
    SubGameResultEvent,
    TurnDecisionEvent,
    TurnExchangeEvent,
)

Banner = str  # "playing" | "capture" | "survival" | "technical_loss" | "disconnected" | "timeout"


@dataclass(frozen=True, slots=True)
class LiveViewModel:
    connection_status: str = "connecting"
    opponent_url: str = ""
    state_machine_state: str = ""
    sub_game_number: int = 0
    step: int = 0
    own_position: tuple[int, int] | None = None
    own_path: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    barriers_remaining: int | None = None
    public_barriers: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    belief: BeliefSnapshot | None = None
    latest_sent_hint: str = ""
    latest_received_hint: str = ""
    strategy_class: str = ""
    decision_latency_seconds: float | None = None
    last_message_type: str = ""
    commit_sent: bool = False
    ack_received: bool = False
    reveal_sent: bool = False
    reveal_received: bool = False
    config_sha256_prefix: str = ""
    banner: Banner = "playing"
    last_result_reason: str = ""
    audit_verdict: str | None = None
    audit_reason: str = ""
    event_log: tuple[str, ...] = field(default_factory=tuple)
    last_event_key: tuple | None = None

    def _logged(self, line: str, limit: int = 200) -> tuple[str, ...]:
        return (*self.event_log, line)[-limit:]


_BANNER_BY_RESULT = {
    "capture": "capture",
    "survival": "survival",
    "technical_loss": "technical_loss",
}


def _event_key(event: object) -> tuple | None:
    """Identity key used to drop an exact-duplicate redelivery of the same
    event (Task 5 "duplicate event idempotency") -- two DIFFERENT events for
    the same step (e.g. decision then exchange) always have different keys
    because the event TYPE is part of the key."""
    if isinstance(event, TurnDecisionEvent | TurnExchangeEvent):
        return (type(event).__name__, event.sub_game_number, event.step)
    if isinstance(event, SubGameResultEvent):
        return (type(event).__name__, event.sub_game_number, event.result)
    if isinstance(event, StateMachineEvent | ConnectionEvent | AuditEvent):
        return (type(event).__name__, event)
    return None


def fold(model: LiveViewModel, event: object) -> LiveViewModel:
    """Pure reducer: given the current model and one new event, return the
    next model. Never raises on a well-formed event; unknown event types
    are ignored (forward-compatible). An event whose identity key exactly
    matches the last-applied event is dropped (idempotent under redelivery)."""
    key = _event_key(event)
    if key is not None and key == model.last_event_key:
        return model
    return replace(_fold_one(model, event), last_event_key=key)


def _fold_one(model: LiveViewModel, event: object) -> LiveViewModel:
    if isinstance(event, ConnectionEvent):
        banner = event.status if event.status in ("disconnected", "timeout") else model.banner
        return replace(
            model,
            connection_status=event.status,
            opponent_url=event.opponent_url,
            banner=banner,
            event_log=model._logged(f"connection: {event.status}"),
        )
    if isinstance(event, StateMachineEvent):
        return replace(
            model,
            state_machine_state=event.state,
            sub_game_number=event.sub_game_number,
            event_log=model._logged(f"state: {event.state}"),
        )
    if isinstance(event, TurnDecisionEvent):
        # A new sub-game number resets the per-sub-game path/banner -- a
        # fresh sub-game starts with a fresh uniform belief and no history
        # carried over (mirrors the real RuntimeState reset per sub-game).
        is_new_sub_game = event.sub_game_number != model.sub_game_number
        prior_path = () if is_new_sub_game else model.own_path
        banner = "playing" if is_new_sub_game else model.banner
        return replace(
            model,
            sub_game_number=event.sub_game_number,
            step=event.step,
            own_position=event.own_position_after,
            own_path=(*prior_path, event.own_position_after),
            barriers_remaining=event.barriers_remaining,
            belief=event.belief,
            latest_sent_hint=event.outgoing_hint_text,
            strategy_class=event.strategy_class,
            decision_latency_seconds=event.decision_latency_seconds,
            banner=banner,
            event_log=model._logged(f"step {event.step}: decided {event.action_selected}"),
        )
    if isinstance(event, TurnExchangeEvent):
        return replace(
            model,
            last_message_type=event.last_message_type,
            commit_sent=event.commit_sent,
            ack_received=event.ack_received,
            reveal_sent=event.reveal_sent,
            reveal_received=event.reveal_received,
            latest_received_hint=event.received_hint_text,
            public_barriers=event.barriers,
            config_sha256_prefix=event.config_sha256_prefix,
            state_machine_state=event.machine_state,
            connection_status="connected" if event.reveal_received else "disconnected",
            event_log=model._logged(f"step {event.step}: {event.last_message_type}"),
        )
    if isinstance(event, SubGameResultEvent):
        return replace(
            model,
            banner=_BANNER_BY_RESULT.get(event.result, "playing"),
            last_result_reason=event.reason,
            state_machine_state=event.machine_state,
            event_log=model._logged(f"sub-game {event.sub_game_number}: {event.result}"),
        )
    if isinstance(event, AuditEvent):
        return replace(
            model,
            audit_verdict=event.verdict,
            audit_reason=event.reason,
            event_log=model._logged(f"audit: {event.verdict}"),
        )
    return model


def field_names() -> tuple[str, ...]:
    return tuple(f.name for f in fields(LiveViewModel))

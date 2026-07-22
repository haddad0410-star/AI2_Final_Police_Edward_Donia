"""Batch 4A Task 3/4: GUI event contract, owned by the services layer (the
turn loop PUBLISHES these; ``gui/`` only ever CONSUMES them).

Every field here is deliberately restricted to what the live GUI is allowed
to show (own truth + public evidence + local belief). No event type in this
module carries the opponent's true position, unrevealed nonce, or the
sealed truth/lie verdict before its legal audit phase -- enforced by
``tests/unit/test_gui_no_opponent_leak.py``'s field-name scanner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class BeliefSnapshot:
    """Local belief about the OPPONENT's likely position -- a probability
    distribution built from public evidence only, never the true cell."""

    grid_size: int
    heatmap: tuple[tuple[float, ...], ...]
    entropy_bits: float
    top_k: tuple[tuple[int, int, float], ...]


@dataclass(frozen=True, slots=True)
class ConnectionEvent:
    status: Literal["connecting", "connected", "disconnected", "timeout"]
    opponent_url: str


@dataclass(frozen=True, slots=True)
class StateMachineEvent:
    state: str
    sub_game_number: int


@dataclass(frozen=True, slots=True)
class TurnDecisionEvent:
    """Published right after this peer picks its own move -- before the
    wire exchange. ``own_position_before``/``after`` are always THIS
    peer's own cell, never the opponent's."""

    sub_game_number: int
    step: int
    own_position_before: tuple[int, int]
    own_position_after: tuple[int, int]
    own_visited_count: int
    action_selected: str
    barrier_placed: tuple[int, int] | None
    barriers_remaining: int
    belief: BeliefSnapshot
    outgoing_hint_text: str
    strategy_class: str
    decision_latency_seconds: float


@dataclass(frozen=True, slots=True)
class TurnExchangeEvent:
    """Published after the commit/ack/reveal exchange for one step
    completes. Protocol sub-step booleans only ever reflect THIS peer's own
    send/receive bookkeeping -- never the opponent's private state."""

    sub_game_number: int
    step: int
    commit_sent: bool
    ack_received: bool
    reveal_sent: bool
    reveal_received: bool
    last_message_type: str
    received_hint_text: str
    barriers: tuple[tuple[int, int], ...]
    config_sha256_prefix: str
    machine_state: str


@dataclass(frozen=True, slots=True)
class SubGameResultEvent:
    sub_game_number: int
    result: Literal["capture", "survival", "technical_loss"]
    reason: str
    steps: int
    police_score: int | None
    thief_score: int | None
    machine_state: str


@dataclass(frozen=True, slots=True)
class AuditEvent:
    sub_game_number: int
    verdict: str
    reason: str


GuiEvent = (
    ConnectionEvent
    | StateMachineEvent
    | TurnDecisionEvent
    | TurnExchangeEvent
    | SubGameResultEvent
    | AuditEvent
)

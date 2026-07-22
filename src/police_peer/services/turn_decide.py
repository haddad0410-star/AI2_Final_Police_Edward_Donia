"""The "think" phase of one turn: advance belief, ask the strategy brain for
a move, prepare the outgoing hint/scent. Split out of ``turn_loop.py`` to
keep both files under the 150-meaningful-line cap; behavior is unchanged,
this is purely a decomposition of the same real logic used since Batch 2.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from police_peer.domain.actions import MoveAction
from police_peer.domain.deadline import DeadlineTracker
from police_peer.domain.hint_region import region_for_intent
from police_peer.domain.hints import HintIntent
from police_peer.domain.rules import apply_move, is_legal_barrier_cell, legal_move_directions
from police_peer.domain.scent import apply_turn
from police_peer.services import turn_gui_publish as gui
from police_peer.services import turn_trace
from police_peer.services.belief_update import advance_belief
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentTransport
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.decision import DecisionRequest
from police_peer.strategy.hint_templates import TemplateHintProvider


@dataclass(slots=True)
class DecideDeps:
    brain: PoliceBrainBase
    hint_provider: TemplateHintProvider
    transport: OpponentTransport
    rng: random.Random
    decay: float
    response_timeout_sec: float


def decide_turn(deps: DecideDeps, state: RuntimeState):
    belief_before = state.belief
    state = advance_belief(state)
    legal = legal_move_directions(state.position, state.board)
    request = DecisionRequest(
        own_position=state.position,
        legal_directions=legal,
        belief=state.belief,
        step=state.step,
        rng=deps.rng,
        deadline=DeadlineTracker(deps.response_timeout_sec).start(),
        board=state.board,
        barriers_remaining=state.barriers_remaining,
        visited=state.visited,
    )
    position_before = state.position
    t0 = time.perf_counter()
    decision = deps.brain.decide(request)
    latency = time.perf_counter() - t0
    if (
        decision.barrier is not None
        and state.barriers_remaining > 0
        and is_legal_barrier_cell(state.position, decision.barrier, state.board)
    ):
        state = state.with_barrier_placed(decision.barrier)
    destination = apply_move(state.position, MoveAction(decision.direction), state.board)
    intent = HintIntent.TRUTH if decision.honest_intent else HintIntent.LIE
    region = region_for_intent(decision.direction, intent, deps.rng)
    hint = deps.hint_provider.generate(intent, deps.rng, region=region)
    new_scent = apply_turn(state.own_scent, destination, deps.decay)
    turn_trace.record_decide_turn(
        state=state,
        belief_before=belief_before,
        brain=deps.brain,
        decision=decision,
        intent=intent,
        hint=hint,
        new_scent=new_scent,
    )
    gui.decision(
        sub_game_number=state.sub_game_number,
        step=state.step,
        position_before=position_before,
        position_after=destination,
        visited_count=len(state.visited),
        action=decision.direction.value,
        barrier=decision.barrier,
        barriers_remaining=state.barriers_remaining,
        belief=state.belief,
        hint_text=hint.text,
        strategy_class=type(deps.brain).__module__ + "." + type(deps.brain).__qualname__,
        latency=latency,
    )
    return state, decision, destination, hint, new_scent

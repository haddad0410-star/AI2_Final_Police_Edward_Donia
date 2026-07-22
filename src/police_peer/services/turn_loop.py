"""The single-sub-game turn loop (Batch 2, Phase 9).

Follows the Phase 2 state machine and the protocol_contract per-step sequence:
think -> commit -> (send) -> ack -> reveal -> verify. Technical failures become
an explicit ``TECHNICAL_LOSS`` outcome via the ``FAIL`` -> ``ERROR`` path; the
loop never hangs. All lifecycle changes route through the state machine.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import SealedRecord, SealedTurnSession
from police_peer.domain.state_machine import EventKind, PeerStateMachine, TransitionEvent
from police_peer.services import turn_gui_publish as gui
from police_peer.services import turn_trace
from police_peer.services.capture_resolution import ingest_opponent_reveal, is_capture_confirmed
from police_peer.services.outcomes import SubGameRunResult
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentTransport, TechnicalFailure
from police_peer.services.turn_decide import DecideDeps, decide_turn
from police_peer.services.turn_payload import (
    build_payload,
    commitment_message,
    envelope,
    reveal_message,
)
from police_peer.strategy.base import PoliceBrainBase
from police_peer.strategy.hint_templates import TemplateHintProvider

E = EventKind


@dataclass(slots=True)
class SubGameContext:
    """Everything one sub-game run needs; ``state`` is replaced functionally."""

    state: RuntimeState
    brain: PoliceBrainBase
    hint_provider: TemplateHintProvider
    transport: OpponentTransport
    machine: PeerStateMachine
    rng: random.Random
    game_uid: str
    config_sha256: str
    max_moves: int
    decay: float
    response_timeout_sec: float

    def decide_deps(self) -> DecideDeps:
        return DecideDeps(
            brain=self.brain,
            hint_provider=self.hint_provider,
            transport=self.transport,
            rng=self.rng,
            decay=self.decay,
            response_timeout_sec=self.response_timeout_sec,
        )


def _result(result: SubGameResult, state: RuntimeState, reason: str, records) -> SubGameRunResult:
    # ``steps`` must match ``len(records)`` -- the number of sealed records
    # actually written to the log -- not ``state.step`` (a separate turn
    # counter that a capture confirmed via the opponent's DELAYED answer can
    # leave one behind, since the confirming exchange still appends a
    # record before the capture check returns; Batch 3.5 Task 9 found this
    # via a real replay-verifier TAMPERED result: "log has 2 steps, result
    # declares 1").
    return SubGameRunResult(
        result=result, steps=len(records), reason=reason, final_state=state, records=tuple(records)
    )


async def run_sub_game(ctx: SubGameContext) -> SubGameRunResult:
    """Run one sub-game to capture / survival / technical-loss termination.

    Assumes the machine is already in ``WAITING`` (the caller performs the
    ``START_SUB_GAME`` / ``NEXT_SUB_GAME`` transition), so the same loop serves
    both the first and subsequent sub-games of a series.
    """
    machine = ctx.machine
    state = ctx.state
    deps = ctx.decide_deps()
    records: list[SealedRecord] = []
    sequence_id = 0
    for _ in range(ctx.max_moves):
        try:
            machine.require(TransitionEvent.of(E.BEGIN_THINKING))
            state, decision, destination, hint, new_scent = decide_turn(deps, state)
            payload = build_payload(
                role=state.role,
                step=state.step,
                sub_game_number=state.sub_game_number,
                destination=destination,
                decision=decision,
                hint=hint,
                own_scent=new_scent,
                config_sha256=ctx.config_sha256,
            )
            session = SealedTurnSession(payload)
            machine.require(TransitionEvent.of(E.COMMIT))
            commit_hash = session.commit()
            machine.require(TransitionEvent.of(E.COMMIT_SENT))
            base = (ctx.game_uid, state.role, state.sub_game_number, state.step)
            commit_msg = commitment_message(envelope(*base, sequence_id), commit_hash)
            reveal_msg = reveal_message(
                envelope(*base, sequence_id + 1), payload.public_reveal_dict()
            )
            opponent = await ctx.transport.exchange_turn(commit_msg, reveal_msg)
            if isinstance(opponent, TechnicalFailure):
                machine.fail(opponent.reason)
                gui.exchange_failed(state, ctx.config_sha256, machine.state.value)
                gui.result_for(
                    state, "technical_loss", opponent.reason, records, machine.state.value
                )
                return _result(SubGameResult.TECHNICAL_LOSS, state, opponent.reason, records)
            session.acknowledge()
            machine.require(TransitionEvent.of(E.ACK_RECEIVED))
            session.reveal()
            machine.require(TransitionEvent.of(E.REVEAL_SENT))
            state = state.moved_to(destination).with_own_scent(new_scent)
            state = ingest_opponent_reveal(state, opponent)
            turn_trace.record_turn_exchange(
                state=state, commit_hash=commit_hash, payload=payload, opponent=opponent
            )
            gui.exchange_ok(state, opponent.hint, ctx.config_sha256, machine.state.value)
            records.append(session.audit_reveal())
            sequence_id += 2
            if is_capture_confirmed(opponent):
                machine.require(TransitionEvent.of(E.SUB_GAME_ENDED))
                gui.result_for(state, "capture", "capture confirmed", records, machine.state.value)
                return _result(SubGameResult.CAPTURE, state, "capture confirmed", records)
            machine.require(TransitionEvent.of(E.TURN_VERIFIED))
            state = state.advanced_step()
        except Exception as exc:  # any runtime fault is a technical loss, never a hang
            machine.fail(str(exc))
            gui.result_for(
                state, "technical_loss", f"runtime error: {exc}", records, machine.state.value
            )
            return _result(SubGameResult.TECHNICAL_LOSS, state, f"runtime error: {exc}", records)
    machine.require(TransitionEvent.of(E.SUB_GAME_ENDED))
    gui.result_for(state, "survival", "thief survived move limit", records, machine.state.value)
    return _result(SubGameResult.SURVIVAL, state, "thief survived move limit", records)

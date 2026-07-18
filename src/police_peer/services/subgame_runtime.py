"""Assemble and run one complete single sub-game (Batch 2, Phase 9 entrypoint).

Builds this peer's OWN initial state from the shared config, loads the private
strategy, and drives the Phase 2 machine SIGNED-ward before the turn loop. The
opponent transport is injected (HTTP in production, a fake in tests).
"""

from __future__ import annotations

import random

from police_peer.domain.belief_updates import uniform_prior
from police_peer.domain.board import Board
from police_peer.domain.positions import Position
from police_peer.domain.roles import Role
from police_peer.domain.scent import empty_scent_field
from police_peer.domain.state_machine import EventKind, PeerStateMachine, TransitionEvent
from police_peer.services.outcomes import SubGameRunResult
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentTransport
from police_peer.services.turn_loop import SubGameContext, run_sub_game
from police_peer.shared.config_models import SharedGameConfig
from police_peer.shared.private_config import PrivateGameConfig
from police_peer.strategy.hint_templates import TemplateHintProvider
from police_peer.strategy.loader import load_police_brain

E = EventKind


def build_initial_state(shared: SharedGameConfig, sub_game_number: int) -> RuntimeState:
    """This peer's own starting state for a fresh sub-game (police at cop_start)."""
    grid = shared.board_and_agents.grid_size
    cop_start = Position(*shared.board_and_agents.cop_start)
    return RuntimeState(
        role=Role.POLICE,
        position=cop_start,
        visited=frozenset({cop_start}),
        board=Board(grid_size=grid),
        barriers_remaining=shared.movement_and_barriers.max_barriers,
        belief=uniform_prior(grid),
        own_scent=empty_scent_field(grid),
        received_scent=empty_scent_field(grid),
        step=0,
        sub_game_number=sub_game_number,
    )


def advance_to_signed(machine: PeerStateMachine) -> None:
    """Drive INITIALIZING -> SERVER_READY -> NEGOTIATING -> SIGNED via the machine."""
    for kind in (E.SERVER_STARTED, E.BEGIN_NEGOTIATION, E.SIGN_TERMS):
        machine.require(TransitionEvent.of(kind))


async def run_single_subgame(
    shared: SharedGameConfig,
    private: PrivateGameConfig,
    transport: OpponentTransport,
    *,
    game_uid: str,
    config_sha256: str,
    sub_game_number: int = 1,
    machine: PeerStateMachine | None = None,
    rng: random.Random | None = None,
) -> SubGameRunResult:
    """Run one sub-game against the injected opponent transport; return its outcome."""
    machine = machine if machine is not None else PeerStateMachine()
    advance_to_signed(machine)
    machine.require(TransitionEvent.of(E.START_SUB_GAME))
    context = build_context(
        shared,
        private,
        transport,
        machine=machine,
        game_uid=game_uid,
        config_sha256=config_sha256,
        sub_game_number=sub_game_number,
        rng=rng if rng is not None else random.Random(private.play.seed),
    )
    return await run_sub_game(context)


def build_context(
    shared: SharedGameConfig,
    private: PrivateGameConfig,
    transport: OpponentTransport,
    *,
    machine: PeerStateMachine,
    game_uid: str,
    config_sha256: str,
    sub_game_number: int,
    rng: random.Random,
) -> SubGameContext:
    """Assemble a :class:`SubGameContext` (machine transitions handled by caller)."""
    return SubGameContext(
        state=build_initial_state(shared, sub_game_number),
        brain=load_police_brain(private.strategy.police_class),
        hint_provider=TemplateHintProvider(shared.world.hint_max_words),
        transport=transport,
        machine=machine,
        rng=rng,
        game_uid=game_uid,
        config_sha256=config_sha256,
        max_moves=shared.movement_and_barriers.max_moves,
        decay=shared.pheromones.pheromone_decay,
        response_timeout_sec=shared.network_and_league.response_timeout_sec,
    )

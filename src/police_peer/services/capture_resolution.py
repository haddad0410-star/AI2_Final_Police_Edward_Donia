"""Resolve publicly-verifiable capture claims and end-of-turn ingestion.

Capture is decided by the opponent's HONEST answer to our claim (we never see
their true position). Ingesting the opponent's reveal updates only legal local
knowledge: their public scent and any barrier they declared.
"""

from __future__ import annotations

from police_peer.domain.positions import Position
from police_peer.domain.scent import ScentField
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentReveal


def is_capture_confirmed(reveal: OpponentReveal) -> bool:
    """True only if the opponent honestly confirmed our capture claim."""
    return reveal.claim_response is True


def ingest_opponent_reveal(state: RuntimeState, reveal: OpponentReveal) -> RuntimeState:
    """Fold the opponent's public reveal into local state (scent + barriers)."""
    grid_size = state.board.grid_size
    if reveal.scent_grid and len(reveal.scent_grid) == grid_size:
        received = ScentField(grid_size=grid_size, grid=reveal.scent_grid)
        state = state.with_received_scent(received)
    if reveal.barrier is not None:
        cell = Position(reveal.barrier[0], reveal.barrier[1])
        if state.board.is_in_bounds(cell):
            state = state.with_board(state.board.with_barrier(cell))
    return state

"""Resolve publicly-verifiable capture claims and end-of-turn ingestion.

Capture is decided by the opponent's HONEST answer to our claim (we never see
their true position). Ingesting the opponent's reveal updates only legal local
knowledge: their public scent, their hint's decoded region, and any barrier
they declared. Never the intent verdict (sealed until final audit) and never
their true position.
"""

from __future__ import annotations

from police_peer.domain.hint_region import parse_region_from_hint, region_cells
from police_peer.domain.positions import Position
from police_peer.domain.scent import ScentField
from police_peer.domain.scent_validation import validate_scent_grid
from police_peer.services.subgame_state import RuntimeState
from police_peer.services.transport import OpponentReveal


def is_capture_confirmed(reveal: OpponentReveal) -> bool:
    """True only if the opponent honestly confirmed our capture claim."""
    return reveal.claim_response is True


def ingest_opponent_reveal(state: RuntimeState, reveal: OpponentReveal) -> RuntimeState:
    """Fold the opponent's public reveal into local state (scent, hint
    region, barriers). A malformed/missing scent grid takes the explicit
    missing-evidence path rather than masquerading as a valid zero reading;
    an unparseable hint is neutral evidence (no region)."""
    grid_size = state.board.grid_size
    if validate_scent_grid(reveal.scent_grid, grid_size) is None:
        grid = tuple(tuple(float(v) for v in row) for row in reveal.scent_grid)
        state = state.with_received_scent(ScentField(grid_size=grid_size, grid=grid), valid=True)
    else:
        state = state.with_no_scent_evidence()
    region_word = parse_region_from_hint(reveal.hint) if reveal.hint else None
    region = region_cells(region_word, grid_size) if region_word else None
    state = state.with_hint_region(region if region else None)
    if reveal.barrier is not None:
        cell = Position(reveal.barrier[0], reveal.barrier[1])
        if state.board.is_in_bounds(cell):
            state = state.with_board(state.board.with_barrier(cell))
    return state

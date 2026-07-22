"""Batch 4A Task 5: reflection-based scanner that fails the build if any
live-GUI-reachable dataclass grows a field equivalent to
``opponent_true_position`` -- run over every dataclass in
``services.gui_events`` and ``gui.view_model`` so a future edit cannot
silently reintroduce a true-position leak into the live GUI.
"""

from __future__ import annotations

import dataclasses

from police_peer.gui import view_model
from police_peer.services import gui_events

_FORBIDDEN_SUBSTRINGS = (
    "opponent_position",
    "opponent_true",
    "true_position",
    "opponent_cell",
    "opponent_coordinate",
    "opponent_location",
    "true_opponent",
)
# opponent_url is an explicit, reviewed exception: it identifies the wire
# endpoint being talked to, never the opponent's board position.
_ALLOWED = {"opponent_url"}


def _all_dataclasses(module) -> list[type]:
    found = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and dataclasses.is_dataclass(obj):
            found.append(obj)
    return found


def test_no_forbidden_field_name_in_gui_events() -> None:
    for cls in _all_dataclasses(gui_events):
        for f in dataclasses.fields(cls):
            if f.name in _ALLOWED:
                continue
            lowered = f.name.lower()
            for bad in _FORBIDDEN_SUBSTRINGS:
                assert bad not in lowered, f"{cls.__name__}.{f.name} looks like a position leak"


def test_no_forbidden_field_name_in_view_model() -> None:
    for cls in _all_dataclasses(view_model):
        for f in dataclasses.fields(cls):
            if f.name in _ALLOWED:
                continue
            lowered = f.name.lower()
            for bad in _FORBIDDEN_SUBSTRINGS:
                assert bad not in lowered, f"{cls.__name__}.{f.name} looks like a position leak"


def test_belief_snapshot_is_a_distribution_not_a_single_cell() -> None:
    """A BeliefSnapshot must always carry a full heatmap grid, never a bare
    single (row, col) -- that shape distinction is itself part of the
    no-leak guarantee (a single cell field would BE a position leak)."""
    fields = {f.name for f in dataclasses.fields(gui_events.BeliefSnapshot)}
    assert "heatmap" in fields
    assert "grid_size" in fields

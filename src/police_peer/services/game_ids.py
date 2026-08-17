"""Deterministic game_id / game_uid derivation (protocol_contract.md 3.1).

Both peers derive these independently from data they already hold -- the sorted
group ids plus the negotiated terms -- so no extra round-trip is needed and
all four JSON artifacts share one identity.

``min_center_intensity`` (moamteam's 14th signed term) is intentionally absent
from ``terms_from_shared_config`` below. Our own config schema treats
``pheromone_min_center_intensity`` as a non-binding optional extension by
deliberate design (docs/risk_register.md risk #2), and two existing tests
(``test_pheromone_extension_tolerance.py::test_extension_never_required_in_baseline``,
``test_shared_config.py::test_pheromone_min_center_intensity_not_present``)
explicitly guard our real config against ever carrying it. Adding it here
would need that decision revisited first, not just this projection edited.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable

from police_peer.shared.config_models import SharedGameConfig


def terms_from_shared_config(shared: SharedGameConfig) -> dict:
    """The flat, cross-team-negotiated terms subset of the shared config,
    keyed by the reference implementation's own term names rather than our
    config file's on-disk section/field names (moamteam, 2026-08-17: the
    signed bytes are the reference's projection, not the file's own
    vocabulary -- our file keeps its own names, only this projection uses
    theirs). ``min_center_intensity`` is deliberately NOT included here yet
    -- see the game_ids.py module docstring note on that field.

    Otherwise deliberately narrower than the whole game.json: schema_version,
    comment fields, agreed_between and rate-limiter minimums are never
    negotiated per-match, so binding the uid to them (as hashing the raw
    file would) ties it to bytes that can differ between two peers who agree
    on every actual game term.
    """
    board = shared.board_and_agents
    world = shared.world
    movement = shared.movement_and_barriers
    pheromones = shared.pheromones
    return {
        "board_size": board.grid_size,
        "thief_start": list(board.thief_start),
        "cop_start": list(board.cop_start),
        "axis_origin_corner": board.axis_origin_corner,
        "axis_start_index": board.axis_start_index,
        "setting": world.map_area,
        "hint_max_words": world.hint_max_words,
        "barriers_max": movement.max_barriers,
        "max_steps": movement.max_moves,
        "emit_intensity": pheromones.pheromone_center_intensity,
        "decay_per_step": pheromones.pheromone_decay,
        "smell_grid_size": pheromones.pheromone_grid_size,
        "num_games": shared.network_and_league.num_games,
    }


def canonical_terms_json(terms: dict) -> str:
    """Canonical JSON for signing/hashing: sorted keys, native UTF-8, compact separators."""
    return json.dumps(terms, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def derive_game_id(group_ids: Iterable[str]) -> str:
    """``"<group_a>-vs-<group_b>"`` (sorted); a single id for local self-play."""
    ids = sorted(group_ids)
    return "-vs-".join(ids) if len(ids) > 1 else (ids[0] if ids else "unknown")


def derive_game_uid(terms: dict, group_ids: Iterable[str]) -> str:
    """A stable UUID over the canonical negotiated terms + sorted group ids.

    NOT a hash of the raw config file (an earlier version of this function
    was): two peers' files can differ in whitespace, comments, or fields
    neither side negotiates while still agreeing on every actual term, and a
    whole-file hash silently diverges the uid in that case even though both
    sides' reports otherwise agree on every value -- a documented cross-team
    failure mode this construction exists to avoid.
    """
    seed = canonical_terms_json(terms) + "|" + "|".join(sorted(group_ids))
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))

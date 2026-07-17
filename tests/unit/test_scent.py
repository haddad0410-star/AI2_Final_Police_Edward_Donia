"""Tests for scent emission/decay -- values visually verified against Ch.4.3, p.28."""

from __future__ import annotations

import dataclasses

from police_peer.domain.positions import Position
from police_peer.domain.scent import (
    EMISSION_MATRIX,
    ScentField,
    ScentHistory,
    apply_turn,
    empty_scent_field,
)

GRID = 7
RHO = 0.10


def test_exact_center_value_after_one_emission() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(3, 3), RHO)
    assert field.value_at(Position(3, 3)) == 0.9


def test_exact_full_5x5_matrix_when_unclipped() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(3, 3), RHO)
    for d_row in range(-2, 3):
        for d_col in range(-2, 3):
            expected = EMISSION_MATRIX[d_row + 2][d_col + 2]
            actual = field.value_at(Position(3 + d_row, 3 + d_col))
            assert actual == expected, f"offset ({d_row},{d_col})"


def test_edge_clipping_does_not_wrap() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(0, 3), RHO)
    # Row offset -1, -2 would be off-board (row -1, -2); must NOT wrap to the
    # bottom rows (5, 6).
    assert field.value_at(Position(GRID - 1, 3)) == 0.0
    assert field.value_at(Position(GRID - 2, 3)) == 0.0
    # The on-board portion of the window still carries the expected values.
    assert field.value_at(Position(0, 3)) == EMISSION_MATRIX[2][2]
    assert field.value_at(Position(1, 3)) == EMISSION_MATRIX[3][2]


def test_corner_clipping() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(0, 0), RHO)
    assert field.value_at(Position(0, 0)) == EMISSION_MATRIX[2][2]
    assert field.value_at(Position(GRID - 1, GRID - 1)) == 0.0
    # Only the bottom-right quadrant of the emission matrix lands on-board.
    assert field.value_at(Position(1, 1)) == EMISSION_MATRIX[3][3]


def test_one_decay_step_with_no_new_emission_nearby() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(3, 3), RHO)
    before = field.value_at(Position(3, 3))
    # Emit far away so cell (3,3) receives zero new emission this turn.
    field = apply_turn(field, Position(0, 0), RHO)
    after = field.value_at(Position(3, 3))
    assert after == before * (1 - RHO)


def test_repeated_decay_compounds() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(3, 3), RHO)
    v1 = field.value_at(Position(3, 3))
    for _ in range(3):
        field = apply_turn(field, Position(0, 0), RHO)
    v_after = field.value_at(Position(3, 3))
    assert v_after == v1 * (1 - RHO) ** 3


def test_re_emission_adds_on_top_of_decayed_residual() -> None:
    field = empty_scent_field(GRID)
    field = apply_turn(field, Position(3, 3), RHO)
    residual = field.value_at(Position(3, 3)) * (1 - RHO)
    field = apply_turn(field, Position(3, 3), RHO)
    assert field.value_at(Position(3, 3)) == residual + EMISSION_MATRIX[2][2]


def test_zero_lower_bound_never_negative() -> None:
    field = empty_scent_field(GRID)
    for _ in range(5):
        field = apply_turn(field, Position(6, 6), RHO)
    assert all(v >= 0.0 for row in field.grid for v in row)


def test_deterministic_history_append_is_immutable() -> None:
    history = ScentHistory()
    field_a = empty_scent_field(GRID)
    field_b = apply_turn(field_a, Position(3, 3), RHO)
    history_1 = history.appended(field_a)
    history_2 = history_1.appended(field_b)
    assert history.snapshots == ()
    assert history_1.snapshots == (field_a,)
    assert history_2.snapshots == (field_a, field_b)


def test_scent_field_has_no_position_leak() -> None:
    """ScentField must only ever describe intensities, never a position field."""
    field_names = {f.name for f in dataclasses.fields(ScentField)}
    assert field_names == {"grid_size", "grid"}

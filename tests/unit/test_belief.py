"""Tests for the normalized probabilistic belief-update model."""

from __future__ import annotations

import inspect
import math

import pytest

from police_peer.domain import belief_updates
from police_peer.domain.belief_model import entropy, most_likely, normalize, top_k
from police_peer.domain.belief_updates import (
    apply_barrier_mask,
    apply_hint_likelihood,
    apply_scent_likelihood,
    apply_transition,
    uniform_prior,
)
from police_peer.domain.positions import Position
from police_peer.domain.scent import apply_turn as scent_apply_turn
from police_peer.domain.scent import empty_scent_field

GRID = 5


def test_uniform_prior_sums_to_one() -> None:
    belief = uniform_prior(GRID)
    assert math.isclose(belief.total_mass(), 1.0, abs_tol=1e-9)


def test_barrier_cells_get_zero_probability() -> None:
    belief = uniform_prior(GRID)
    barrier = Position(2, 2)
    updated = apply_barrier_mask(belief, [barrier])
    assert updated.probability_at(barrier) == 0.0
    assert math.isclose(updated.total_mass(), 1.0, abs_tol=1e-9)


def test_impossible_cells_from_prior_barriers_are_zero() -> None:
    belief = uniform_prior(GRID, barriers=[Position(0, 0)])
    assert belief.probability_at(Position(0, 0)) == 0.0


def test_transition_moves_mass_to_legal_neighbors_only() -> None:
    belief = normalize(GRID, [[0.0] * GRID for _ in range(GRID)])
    raw = [[0.0] * GRID for _ in range(GRID)]
    raw[2][2] = 1.0
    belief = normalize(GRID, raw)

    def neighbors(p: Position):
        return [Position(p.row, p.col + 1), Position(p.row, p.col - 1)]

    updated = apply_transition(belief, neighbors)
    assert updated.probability_at(Position(2, 3)) == pytest.approx(0.5)
    assert updated.probability_at(Position(2, 1)) == pytest.approx(0.5)
    assert updated.probability_at(Position(2, 2)) == 0.0


def test_scent_likelihood_increases_probability_at_hot_cells() -> None:
    belief = uniform_prior(GRID)
    scent = scent_apply_turn(empty_scent_field(GRID), Position(2, 2), 0.10)
    updated = apply_scent_likelihood(belief, scent, trust=1.0)
    assert updated.probability_at(Position(2, 2)) > belief.probability_at(Position(2, 2))
    assert math.isclose(updated.total_mass(), 1.0, abs_tol=1e-9)


def test_scent_likelihood_all_zero_is_a_safe_noop() -> None:
    belief = uniform_prior(GRID)
    scent = empty_scent_field(GRID)
    updated = apply_scent_likelihood(belief, scent)
    for r in range(GRID):
        for c in range(GRID):
            assert updated.grid[r][c] == pytest.approx(belief.grid[r][c])


def test_hint_likelihood_boosts_agreeing_region() -> None:
    belief = uniform_prior(GRID)
    region = [Position(0, 0), Position(0, 1)]
    updated = apply_hint_likelihood(belief, region, base_trust=0.5)
    assert updated.probability_at(Position(0, 0)) > belief.probability_at(Position(0, 0))


def test_contradictory_hint_is_down_weighted_not_corrupting() -> None:
    """A region the scent evidence already rules out gets a much smaller
    boost than a region already supported by evidence -- never overrides
    physical impossibility (a hard-zeroed cell stays zero)."""
    belief = uniform_prior(GRID)
    scent = scent_apply_turn(empty_scent_field(GRID), Position(4, 4), 0.10)
    belief = apply_scent_likelihood(belief, scent, trust=5.0)

    contradicted_region = [Position(0, 0)]
    supported_region = [Position(4, 4)]

    boosted_contradicted = apply_hint_likelihood(belief, contradicted_region, base_trust=0.5)
    boosted_supported = apply_hint_likelihood(belief, supported_region, base_trust=0.5)

    gain_contradicted = boosted_contradicted.probability_at(Position(0, 0)) - belief.probability_at(
        Position(0, 0)
    )
    gain_supported = boosted_supported.probability_at(Position(4, 4)) - belief.probability_at(
        Position(4, 4)
    )
    assert gain_contradicted < gain_supported

    # A hint can never revive a hard-zeroed (physically impossible) cell.
    belief_with_barrier = apply_barrier_mask(belief, [Position(1, 1)])
    hinted = apply_hint_likelihood(belief_with_barrier, [Position(1, 1)], base_trust=0.9)
    assert hinted.probability_at(Position(1, 1)) == 0.0


def test_degenerate_all_zero_evidence_falls_back_to_uniform() -> None:
    belief = normalize(GRID, [[0.0] * GRID for _ in range(GRID)])
    assert math.isclose(belief.total_mass(), 1.0, abs_tol=1e-9)
    expected = 1.0 / (GRID * GRID)
    assert belief.probability_at(Position(0, 0)) == pytest.approx(expected)


def test_entropy_uniform_is_maximal_for_grid_size() -> None:
    belief = uniform_prior(GRID)
    max_entropy = math.log2(GRID * GRID)
    assert entropy(belief) == pytest.approx(max_entropy)


def test_entropy_certain_belief_is_zero() -> None:
    raw = [[0.0] * GRID for _ in range(GRID)]
    raw[1][1] = 1.0
    belief = normalize(GRID, raw)
    assert entropy(belief) == pytest.approx(0.0, abs=1e-9)


def test_most_likely_and_top_k() -> None:
    raw = [[0.0] * GRID for _ in range(GRID)]
    raw[1][1] = 0.7
    raw[2][2] = 0.3
    belief = normalize(GRID, raw)
    assert most_likely(belief) == Position(1, 1)
    top2 = top_k(belief, 2)
    assert top2[0][0] == Position(1, 1)
    assert top2[1][0] == Position(2, 2)


def test_no_function_accepts_an_opponent_true_position_parameter() -> None:
    """Structural guarantee: nothing in this module can be given the
    opponent's true position, because no function signature has a parameter
    for it."""
    suspicious = ("opponent_position", "opponent_true_position", "true_position", "enemy_position")
    for name, fn in inspect.getmembers(belief_updates, inspect.isfunction):
        params = set(inspect.signature(fn).parameters)
        assert not (params & set(suspicious)), f"{name} has a suspicious parameter"

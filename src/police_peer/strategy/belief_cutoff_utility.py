"""Scoring helpers for :class:`BeliefCutoffPoliceBrain` (Batch 3, Task 3).

Every function here is a pure function of PUBLIC information already
carried on a :class:`~police_peer.strategy.decision.DecisionRequest` (own
position, belief, board, visited set) -- none accepts or could accept an
opponent-true-position argument.
"""

from __future__ import annotations

from collections import deque

from police_peer.domain.belief_model import BeliefMap, expected_distance, top_k
from police_peer.domain.belief_updates import apply_transition
from police_peer.domain.board import Board
from police_peer.domain.positions import Position
from police_peer.strategy.belief_cutoff_config import BeliefCutoffWeights


def manhattan(a: Position, b: Position) -> int:
    return abs(a.row - b.row) + abs(a.col - b.col)


def _neighbors_including_stay(board: Board):
    def fn(p: Position):
        if board.is_barrier(p):
            return ()
        return (p, *(c for c in board.adjacent_cells(p) if not board.is_barrier(c)))

    return fn


def project_belief(belief: BeliefMap, board: Board, depth: int) -> BeliefMap:
    """Bounded lookahead (Task 3D): spread ``belief`` forward ``depth`` legal
    transition steps (self-or-orthogonal-neighbor diffusion, respecting
    barriers) using the same ``apply_transition`` primitive the real belief
    pipeline uses -- never treats the projection as certain, only as a
    forward-looking pursuit signal."""
    projected = belief
    neighbors_fn = _neighbors_including_stay(board)
    for _ in range(max(0, depth)):
        projected = apply_transition(projected, neighbors_fn)
    return projected


def score_move(
    *,
    origin: Position,
    destination: Position,
    belief: BeliefMap,
    projected_belief: BeliefMap,
    visited: frozenset[Position],
    top_k_cells: tuple,
    exploring: bool,
    weights: BeliefCutoffWeights,
) -> float:
    """Higher is better. Combines immediate belief-weighted pursuit,
    bounded-lookahead pursuit, a top-k capture-opportunity bonus, a
    revisit penalty, and (only while entropy is high) a frontier bonus for
    moving toward a cell the belief distribution says little about."""
    origin_ed = expected_distance(belief, origin, manhattan)
    dest_ed = expected_distance(belief, destination, manhattan)
    score = weights.expected_distance * (origin_ed - dest_ed)

    projected_ed = expected_distance(projected_belief, destination, manhattan)
    score += weights.lookahead_distance * (origin_ed - projected_ed)

    if any(cell == destination for cell, _ in top_k_cells):
        score += weights.capture_opportunity

    if destination in visited:
        score -= weights.revisit_penalty

    # Frontier bonus: prefer the LEAST-likely-to-already-be-well-modeled cell
    # among candidates, approximated by low belief mass (unexplored in the
    # probabilistic sense) and not previously visited.
    if (
        exploring
        and destination not in visited
        and belief.probability_at(destination) < (1.0 / (belief.grid_size * belief.grid_size))
    ):
        score += weights.frontier_bonus

    return score


def reachable_area(board: Board, extra_barrier: Position | None, start: Position) -> int:
    """BFS flood-fill cell count reachable from ``start`` if ``extra_barrier``
    were added -- the real (not hand-waved) measure behind "expected
    reduction in Thief reachable area" / "corridor closure" (Task 3E)."""
    blocked = board.barriers | ({extra_barrier} if extra_barrier else set())
    if start in blocked:
        return 0
    seen = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for neighbor in board.adjacent_cells(cell):
            if neighbor in blocked or neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)
    return len(seen)


def barrier_utility(
    *,
    cell: Position,
    board: Board,
    belief: BeliefMap,
    barriers_remaining: int,
    max_barriers: int,
    weights: BeliefCutoffWeights,
) -> float:
    """Higher is better. See docs/STRATEGY.md for the full formula."""
    baseline_area = reachable_area(board, None, _believed_region_seed(belief))
    reduced_area = reachable_area(board, cell, _believed_region_seed(belief))
    area_reduction = max(0, baseline_area - reduced_area)
    score = weights.barrier_area_reduction * (area_reduction / max(1, baseline_area))

    likely_cell = top_k(belief, 1)[0][0]
    proximity = 1.0 / (1.0 + manhattan(cell, likely_cell))
    score += weights.barrier_belief_proximity * proximity

    scarcity = 1.0 - (barriers_remaining / max(1, max_barriers))
    score -= weights.barrier_scarcity_penalty * scarcity

    return score


def _believed_region_seed(belief: BeliefMap) -> Position:
    return top_k(belief, 1)[0][0]

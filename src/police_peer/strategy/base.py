"""PoliceBrainBase: the single, isolated move-selection seam.

``decide`` wraps ``_pick_move`` with the universal safety invariants from
``strategy_proposals.md`` Section 0: always return SOME legal move, never raise,
never block, never return ``None``. A brain is never given a reference to the
lifecycle state machine, so strategy code cannot alter peer lifecycle state.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from police_peer.domain.positions import Direction
from police_peer.strategy.decision import Decision, DecisionRequest

_LOG = logging.getLogger("police_peer.strategy")


class PoliceBrainBase(ABC):
    """Base class for all police move-selection strategies."""

    @abstractmethod
    def _pick_move(self, request: DecisionRequest) -> Decision:
        """Choose a move; subclasses override this. May assume legal_directions is non-empty."""

    def decide(self, request: DecisionRequest) -> Decision:
        """Return a legal :class:`Decision`, falling back safely on any failure.

        The fallback (first legal direction, else STAY) guarantees the peer
        always has a legal move before its deadline, no matter what a subclass
        does internally.
        """
        if not request.legal_directions:
            return Decision(direction=Direction.STAY)
        try:
            decision = self._pick_move(request)
        except Exception as exc:  # invariant 4: never crash the peer, always move
            _LOG.warning("strategy fell back after internal error: %s", exc)
            return Decision(direction=request.legal_directions[0])
        if decision.direction not in request.legal_directions:
            _LOG.warning("strategy returned illegal move %s; falling back", decision.direction)
            return Decision(direction=request.legal_directions[0])
        return decision

"""Bounded hint-trust tracking for :class:`BeliefCutoffPoliceBrain`
(Batch 3, Task 3F).

Scope note: the current wire protocol folds the opponent's verbal hint into
the LOCAL belief update upstream (``services/belief_update.py``) before a
brain ever sees anything -- ``DecisionRequest`` carries only the resulting
``belief`` distribution, not raw hint text (see ADR note in
``docs/STRATEGY.md``). This tracker therefore uses the real, observable
proxy available to the brain -- whether each turn's belief update reduced
entropy (informative/consistent evidence) or increased it (contradictory or
uninformative evidence) -- rather than fabricating access to raw hint text
the architecture does not currently deliver to strategy code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_MIN_TRUST = 0.0
_MAX_TRUST = 1.0
_INITIAL_TRUST = 0.5
_GAIN_ON_INFORMATIVE = 0.05
_LOSS_ON_CONTRADICTORY = 0.10


@dataclass(slots=True)
class HintTrustTracker:
    """A bounded [0, 1] running trust score; one instance lives for the
    duration of a single sub-game (fresh per sub-game, matching the brain's
    own lifecycle)."""

    trust: float = field(default=_INITIAL_TRUST)
    _last_entropy: float | None = field(default=None, repr=False)

    def observe(self, current_entropy: float) -> float:
        """Update trust from the entropy delta since the last observed
        turn; returns the new trust value. The very first call only
        records a baseline (no prior entropy to compare against)."""
        if self._last_entropy is not None:
            if current_entropy < self._last_entropy - 1e-9:
                self.trust = min(_MAX_TRUST, self.trust + _GAIN_ON_INFORMATIVE)
            elif current_entropy > self._last_entropy + 1e-9:
                self.trust = max(_MIN_TRUST, self.trust - _LOSS_ON_CONTRADICTORY)
        self._last_entropy = current_entropy
        return self.trust

    def scaled_explore_threshold(self, base_threshold: float) -> float:
        """Lower trust -> lower explore threshold (fall back to exploration
        sooner when recent evidence has been unreliable); never negative."""
        return max(0.0, base_threshold * (0.5 + self.trust))

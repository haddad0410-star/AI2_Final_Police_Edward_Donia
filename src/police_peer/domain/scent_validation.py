"""Validation for a received public scent grid (Batch 3.5 Task 4).

A malformed grid (wrong shape, non-numeric, non-finite, negative, or
exceeding the physically-reachable steady-state maximum for the binding
emission/decay model) must never be silently treated as valid evidence --
see `observation_pipeline_audit.md` (defect A1) and `pipeline_before_after.md`
(development-workspace evidence, not included in this standalone package).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from police_peer.domain.scent import EMISSION_MATRIX

_PEAK_EMISSION = max(v for row in EMISSION_MATRIX for v in row)
_BINDING_DECAY = 0.10
#: Steady-state bound for a cell repeatedly re-emitted at the peak intensity
#: under decay rho: x* = peak / rho (0.9 / 0.10 = 9.0); +5% float margin.
LEGAL_MAX_VALUE = _PEAK_EMISSION / _BINDING_DECAY * 1.05


def validate_scent_grid(grid: object, grid_size: int) -> str | None:
    """Return ``None`` if ``grid`` is a legal scent grid, else a short
    machine-readable rejection reason (never raises)."""
    if grid is None:
        return "missing"
    if isinstance(grid, str | bytes) or not isinstance(grid, Sequence) or len(grid) != grid_size:
        return "bad_dimensions"
    for row in grid:
        if isinstance(row, str | bytes) or not isinstance(row, Sequence) or len(row) != grid_size:
            return "bad_dimensions"
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int | float):
                return "non_numeric"
            if not math.isfinite(value):
                return "non_finite"
            if value < 0.0:
                return "negative"
            if value > LEGAL_MAX_VALUE:
                return "exceeds_legal_maximum"
    return None

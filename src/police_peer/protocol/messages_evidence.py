"""Evidence-carrying messages: hint, scent payload, barrier declaration."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.protocol.envelope import MessageEnvelope
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class HintMessage:
    """A free natural-language hint; may lie in `text`, never in `intent`."""

    envelope: MessageEnvelope
    text: str
    intent: str  # "truth" | "lie"

    def __post_init__(self) -> None:
        if self.intent not in ("truth", "lie"):
            raise SchemaValidationError(f"invalid hint intent: {self.intent!r}")

    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True, slots=True)
class ScentPayloadMessage:
    """The sender's own scent grid, as public evidence for the opponent."""

    envelope: MessageEnvelope
    grid_size: int
    grid: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if self.grid_size < 1:
            raise SchemaValidationError("grid_size must be >= 1")
        if len(self.grid) != self.grid_size:
            raise SchemaValidationError("grid row count must equal grid_size")
        for row in self.grid:
            if len(row) != self.grid_size:
                raise SchemaValidationError("grid column count must equal grid_size")
            if any(v < 0 for v in row):
                raise SchemaValidationError("scent values must be >= 0")


@dataclass(frozen=True, slots=True)
class BarrierDeclarationMessage:
    """Police's mandatory, truthful public declaration of a barrier's cell."""

    envelope: MessageEnvelope
    cell_row: int
    cell_col: int

    def __post_init__(self) -> None:
        if self.cell_row < 0 or self.cell_col < 0:
            raise SchemaValidationError("cell_row/cell_col must be >= 0")

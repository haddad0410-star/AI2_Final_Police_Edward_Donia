"""Turn commit/reveal message shapes (schemas only -- see module docstring in
messages_handshake.py: the full lifecycle is wired up in a later batch)."""

from __future__ import annotations

from dataclasses import dataclass

from police_peer.protocol.envelope import MessageEnvelope
from police_peer.shared.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class TurnCommitmentMessage:
    """Step 1 of commit-reveal: H_commit only, nothing else revealed yet."""

    envelope: MessageEnvelope
    commit_hash: str

    def __post_init__(self) -> None:
        if len(self.commit_hash) != 64:
            raise SchemaValidationError("commit_hash must be a 64-char hex digest")


@dataclass(frozen=True, slots=True)
class TurnRevealMessage:
    """Step 3 of commit-reveal: move + hint revealed, nonce still hidden."""

    envelope: MessageEnvelope
    move_direction: str | None
    barrier_cell: tuple[int, int] | None
    hint_text: str
    hint_intent: str

    def __post_init__(self) -> None:
        if self.hint_intent not in ("truth", "lie"):
            raise SchemaValidationError(f"invalid hint intent: {self.hint_intent!r}")
        if self.move_direction is None and self.barrier_cell is None:
            raise SchemaValidationError("exactly one of move_direction/barrier_cell required")
        if self.move_direction is not None and self.barrier_cell is not None:
            raise SchemaValidationError("only one of move_direction/barrier_cell may be set")


@dataclass(frozen=True, slots=True)
class PublicTurnEnvelopeMessage:
    """The full public-wire shape of one peer's turn, for logging/replay."""

    envelope: MessageEnvelope
    hint_text: str
    hint_intent: str
    scent_grid: tuple[tuple[float, ...], ...]
    barrier_placed: tuple[int, int] | None = None
    capture_claim: tuple[int, int] | None = None
    claim_response_caught: bool | None = None
    win_claim: bool = False

    def __post_init__(self) -> None:
        if self.hint_intent not in ("truth", "lie"):
            raise SchemaValidationError(f"invalid hint intent: {self.hint_intent!r}")

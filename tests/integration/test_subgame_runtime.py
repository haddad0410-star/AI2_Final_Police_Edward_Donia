"""Phase 9: single sub-game runtime against an in-process fake opponent.

Mocks/fakes are test-only; this exercises the full turn lifecycle, capture
resolution, and the technical-loss path without any real network.
"""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import audit_records
from police_peer.domain.state_machine import PeerState, PeerStateMachine
from police_peer.services import subgame_runtime as sr
from police_peer.services.subgame_runtime import run_single_subgame
from police_peer.services.transport import OpponentReveal, TechnicalFailure
from police_peer.shared.config_loader import load_private_config, load_shared_config, sha256_hex

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"
GRID = 7
ZERO_SCENT = tuple(tuple(0.0 for _ in range(GRID)) for _ in range(GRID))


def _load():
    shared = load_shared_config(CONFIG_DIR / "game.json")
    private = load_private_config(CONFIG_DIR / "game.toml")
    config_sha = sha256_hex(CONFIG_DIR / "game.json")
    return shared, private, config_sha


class ScriptedTransport:
    """Replays a fixed list of opponent reveals; defaults to 'not caught'."""

    def __init__(self, reveals: list[OpponentReveal]) -> None:
        self._reveals = reveals
        self._i = 0
        self.sent: list[dict] = []

    async def exchange_turn(self, commitment, reveal):
        self.sent.append(commitment)
        if self._i < len(self._reveals):
            r = self._reveals[self._i]
            self._i += 1
            return r
        return OpponentReveal(
            move="STAY", hint="quiet", scent_grid=ZERO_SCENT, claim_response=False
        )


class FailingTransport:
    async def exchange_turn(self, commitment, reveal):
        return TechnicalFailure("opponent sent a malformed reply")


def _run(transport, machine=None):
    shared, private, config_sha = _load()
    return asyncio.run(
        run_single_subgame(
            shared,
            private,
            transport,
            game_uid="uid-test",
            config_sha256=config_sha,
            sub_game_number=1,
            machine=machine,
            rng=random.Random(7),
        )
    )


def test_capture_happy_path() -> None:
    reveals = [OpponentReveal("STAY", "hi", ZERO_SCENT, claim_response=False) for _ in range(3)]
    reveals.append(OpponentReveal("STAY", "caught", ZERO_SCENT, claim_response=True))
    machine = PeerStateMachine()
    result = _run(ScriptedTransport(reveals), machine)
    assert result.result is SubGameResult.CAPTURE
    assert machine.state is PeerState.SUB_GAME_OVER
    assert len(result.records) == 4  # one sealed record per turn played


def test_survival_when_never_caught() -> None:
    machine = PeerStateMachine()
    result = _run(ScriptedTransport([]), machine)  # transport always answers 'not caught'
    assert result.result is SubGameResult.SURVIVAL
    assert result.steps == 35  # ran to the move limit
    assert machine.state is PeerState.SUB_GAME_OVER


def test_technical_loss_on_malformed_opponent() -> None:
    machine = PeerStateMachine()
    result = _run(FailingTransport(), machine)
    assert result.result is SubGameResult.TECHNICAL_LOSS
    assert machine.state is PeerState.ERROR
    assert result.is_technical_loss is True


def test_sealed_records_audit_clean() -> None:
    reveals = [OpponentReveal("STAY", "hi", ZERO_SCENT, claim_response=True)]
    result = _run(ScriptedTransport(reveals))
    assert audit_records(result.records).ok is True  # our own records self-verify


def test_runtime_state_has_no_opponent_position_field() -> None:
    import dataclasses

    from police_peer.services.subgame_state import RuntimeState

    names = {f.name for f in dataclasses.fields(RuntimeState)}
    for forbidden in ("opponent", "true_position", "thief_position", "enemy"):
        assert not any(forbidden in n for n in names), names


def test_services_source_has_no_forbidden_field_names() -> None:
    services_dir = Path(sr.__file__).resolve().parent
    forbidden = ("opponent_true_position", "opponent_position", "thief_true_position")
    for path in services_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, f"{needle} in {path.name}"

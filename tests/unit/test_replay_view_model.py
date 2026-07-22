"""Batch 4B Task 3/4: headless tests for the graphical replay viewer's data
layer and playback navigation, now covering FULL BILATERAL verification.
No Tkinter import anywhere in this file.

Both the Police and "Thief" fixtures below are built with THIS repo's own
real crypto module (``SealedRecord``/``compute_commit_hash``) using the
current ``commitment/1`` canonical schema -- this is realistic: after
Batch 4B Task 3 unified the sealed field set, a genuinely Thief-produced
``commitment/1`` record is byte-for-byte reconstructable by Police's own
verifier (same field set, same shared canonical-JSON algorithm), so using
Police's own crypto module to build a role="thief" fixture exercises
EXACTLY the same code path Police's verifier will exercise against a real
Thief artifact. A separate legacy-schema fixture (old ``sealed-turn/2``
shape) proves the pre-Batch-4B display-only fallback still works for old
evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.domain.captures import SubGameResult
from police_peer.domain.crypto import AuditResult, AuditVerdict, SealedRecord, compute_commit_hash
from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.gui.replay_playback import PlaybackState
from police_peer.gui.replay_view_model import build_replay_view
from police_peer.services.artifact_builders import build_log_artifact, build_result_artifact
from police_peer.services.artifact_models import ConfigArtifact
from police_peer.services.artifacts import (
    config_filename,
    log_filename,
    result_filename,
    save_artifact,
)
from police_peer.services.series_runtime import SeriesResult
from police_peer.services.series_scoring import FinalAgreement, SubGameRecord
from police_peer.shared.canonical_json import canonical_json_bytes
from police_peer.shared.config_loader import sha256_hex

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "police"
UID = "abcabcab-1111-2222-3333-444444444444"
GID = "edward-donia"
N_GAMES = 2
STEPS_PER_GAME = 3


def _payload(role: str, sub_game: int, step: int, *, col_offset: int = 0) -> SealedTurnPayload:
    return SealedTurnPayload(
        step=step,
        role=role,
        sub_game_number=sub_game,
        position=(step, col_offset),
        move="S" if role == "police" else "E",
        barrier_placed=[2, 2] if (role == "police" and step == 1) else None,
        intent="truth",
        hint="south looks fine" if role == "police" else "east looks fine",
        scent_digest="d" * 64,
        scent_grid=((0.0, 0.0), (0.0, 0.0)),
        capture_claim=(step, col_offset) if role == "police" else None,
        claim_response=True if role == "thief" else None,
        win_claim=False,
        config_sha256=sha256_hex(CONFIG_DIR / "game.json"),
        timestamp="2026-07-18T00:00:00+00:00",
        nonce=f"{sub_game:032x}{step:032x}{role[0]}",
    )


def _write_bundle(directory: Path, role: str, winner: str, *, col_offset: int = 0) -> None:
    with open(CONFIG_DIR / "game.json", encoding="utf-8") as handle:
        terms = json.load(handle)
    config_sha = sha256_hex(CONFIG_DIR / "game.json")
    for n in range(1, N_GAMES + 1):
        recs = tuple(
            SealedRecord(
                _payload(role, n, s, col_offset=col_offset),
                compute_commit_hash(_payload(role, n, s, col_offset=col_offset)),
            )
            for s in range(STEPS_PER_GAME)
        )
        save_artifact(
            ConfigArtifact(UID, GID, n, config_sha, terms), directory / config_filename(GID, n)
        )
        log = build_log_artifact(UID, GID, n, recs, AuditResult(AuditVerdict.VERIFIED, "ok"))
        save_artifact(log, directory / log_filename(GID, n))
    sub_records = tuple(
        SubGameRecord(n, SubGameResult.CAPTURE, 20, 5, STEPS_PER_GAME, True)
        for n in range(1, N_GAMES + 1)
    )
    series = SeriesResult(
        sub_records, FinalAgreement(True, "agreed", 20 * N_GAMES, 5 * N_GAMES), "completed", None
    )
    result = build_result_artifact(UID, GID, "deadbeef", GID, config_sha, series)
    save_artifact(result, directory / result_filename(GID))
    decl = {"schema_version": "declaration/1", "game_uid": UID, "game_id": GID, "role": role}
    (directory / f"declaration_{GID}.json").write_bytes(canonical_json_bytes(decl) + b"\n")


def _write_police_bundle(directory: Path) -> None:
    _write_bundle(directory, "police", "police", col_offset=0)


def _write_thief_bundle(directory: Path) -> None:
    """A real, cryptographically-valid ``commitment/1`` Thief-shaped
    bundle -- built with Police's own crypto module (see module docstring
    for why this is a realistic proxy for a genuine Thief artifact)."""
    _write_bundle(directory, "thief", "police", col_offset=1)


def _write_legacy_thief_bundle(directory: Path) -> None:
    """A real Thief-shaped bundle using the OLD ``sealed-turn/2`` schema
    (string ``state``, no top-level ``position``/``config_sha256``) --
    proves the pre-Batch-4B legacy fallback still works honestly."""
    with open(CONFIG_DIR / "game.json", encoding="utf-8") as handle:
        terms = json.load(handle)
    config_sha = sha256_hex(CONFIG_DIR / "game.json")
    for n in range(1, N_GAMES + 1):
        steps = [
            {
                "step": s,
                "role": "thief",
                "sub_game_number": n,
                "state": f"pos={s},1;visited=1",
                "move": "E",
                "hint": "east",
                "barrier_placed": None,
                "capture_claim": None,
                "claim_response": None,
                "win_claim": False,
                "commit_hash": "a" * 64,
                "nonce": "b" * 64,
                "timestamp": "2026-07-18T00:00:00+00:00",
                "config_sha256": config_sha,
                "schema_version": "sealed-turn/2",
                "scent_digest": "c" * 64,
                "scent_grid": [[0.0, 0.0], [0.0, 0.0]],
                "intent": "truth",
            }
            for s in range(STEPS_PER_GAME)
        ]
        (directory / config_filename(GID, n)).write_text(
            json.dumps(
                {
                    "game_uid": UID,
                    "game_id": GID,
                    "sub_game_number": n,
                    "config_sha256": config_sha,
                    "terms": terms,
                }
            )
        )
        (directory / log_filename(GID, n)).write_text(
            json.dumps(
                {
                    "game_uid": UID,
                    "game_id": GID,
                    "sub_game_number": n,
                    "steps": steps,
                    "audit_verdict": "verified",
                    "audit_reason": "ok",
                }
            )
        )
    sub_games = [
        {
            "sub_game_number": n,
            "result": "capture",
            "winner": "police",
            "police_score": 20,
            "thief_score": 5,
            "steps": STEPS_PER_GAME,
            "audit_ok": True,
        }
        for n in range(1, N_GAMES + 1)
    ]
    (directory / result_filename(GID)).write_text(
        json.dumps(
            {
                "game_uid": UID,
                "game_id": GID,
                "config_sha256": config_sha,
                "sub_games": sub_games,
                "police_total": 40,
                "thief_total": 10,
            }
        )
    )
    (directory / f"declaration_{GID}.json").write_text(
        json.dumps(
            {"schema_version": "declaration/1", "game_uid": UID, "game_id": GID, "role": "thief"}
        )
    )


def _model(tmp_path: Path):
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    return build_replay_view(police_dir, thief_dir)


def test_valid_six_sub_game_like_set_fully_bilaterally_verified(tmp_path) -> None:
    model = _model(tmp_path)
    assert model.verdict == "VERIFIED"
    assert model.verification_ok is True
    assert model.full_bilateral_verification is True
    assert len(model.sub_games) == N_GAMES


def test_both_sides_independently_verified(tmp_path) -> None:
    """The real fix this batch delivers: Police's OWN verifier can now
    correctly recompute a Thief-shaped commitment/1 record's hash -- no
    display-only exception for current-schema records (Rule 9)."""
    model = _model(tmp_path)
    assert model.police.independently_verified is True
    assert model.police.verdict == "VERIFIED"
    assert model.thief.independently_verified is True
    assert model.thief.verdict == "VERIFIED"


def test_legacy_opponent_schema_still_uses_documented_fallback(tmp_path) -> None:
    """Rule 10: a LEGACY (pre-commitment/1) opponent record may still be
    display-only, honestly labeled -- never silently claimed VERIFIED."""
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_legacy_thief_bundle(thief_dir)
    model = build_replay_view(police_dir, thief_dir)
    assert model.thief.independently_verified is False
    assert "LEGACY_SCHEMA" in model.thief.verdict
    assert model.full_bilateral_verification is False


def test_tampered_thief_commitment_is_detected_by_police(tmp_path) -> None:
    """The other real fix: Police's verifier must actually DETECT a
    tampered Thief commitment/1 record, not just fail to crash."""
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    log_path = thief_dir / log_filename(GID, 1)
    data = json.loads(log_path.read_text())
    data["steps"][0]["move"] = "N"  # tamper after sealing
    log_path.write_text(json.dumps(data))
    model = build_replay_view(police_dir, thief_dir)
    assert model.thief.independently_verified is True
    assert model.thief.verdict == "TAMPERED"
    assert model.full_bilateral_verification is False
    assert model.verification_ok is False


def test_both_true_paths_present(tmp_path) -> None:
    model = _model(tmp_path)
    sg = model.sub_games[0]
    assert sg.police_steps[0].position == (0, 0)
    assert sg.thief_steps[0].position == (0, 1)


def test_barriers_present(tmp_path) -> None:
    model = _model(tmp_path)
    assert model.sub_games[0].barriers == ((2, 2),)


def test_score_display(tmp_path) -> None:
    model = _model(tmp_path)
    assert model.sub_games[0].police_score == 20
    assert model.sub_games[0].thief_score == 5


def test_sub_game_selection(tmp_path) -> None:
    model = _model(tmp_path)
    playback = PlaybackState()
    playback.select(model, 1)
    assert playback.sub_game_index == 1
    assert playback.step == 0


def test_playback_order_and_step_navigation(tmp_path) -> None:
    model = _model(tmp_path)
    playback = PlaybackState()
    playback.next(model)
    playback.next(model)
    assert playback.step == 2
    playback.prev()
    assert playback.step == 1
    playback.jump_end(model)
    assert playback.step == playback.max_step(model)
    playback.jump_start()
    assert playback.step == 0


def test_pause_resume(tmp_path) -> None:
    playback = PlaybackState()
    assert playback.playing is False
    playback.toggle_play()
    assert playback.playing is True
    playback.toggle_play()
    assert playback.playing is False


def test_playback_tick_advances_and_stops_at_end(tmp_path) -> None:
    model = _model(tmp_path)
    playback = PlaybackState()
    playback.playing = True
    advanced = playback.advance_if_playing(model)
    assert advanced is True
    playback.step = playback.max_step(model)
    advanced_at_end = playback.advance_if_playing(model)
    assert advanced_at_end is False
    assert playback.playing is False


def test_missing_log_is_reflected_as_empty_steps(tmp_path) -> None:
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    (police_dir / log_filename(GID, 2)).unlink()
    model = build_replay_view(police_dir, thief_dir)
    assert model.verification_ok is False
    assert any("missing" in f.lower() or "count" in f.lower() for f in model.police.findings)


def test_duplicate_log_is_detected(tmp_path) -> None:
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    data = json.loads((police_dir / log_filename(GID, 2)).read_text())
    data["sub_game_number"] = 1
    (police_dir / log_filename(GID, 2)).write_text(json.dumps(data))
    model = build_replay_view(police_dir, thief_dir)
    assert model.verification_ok is False
    assert any("duplicate" in f.lower() for f in model.police.findings)


def test_wrong_game_uid_is_detected(tmp_path) -> None:
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    data = json.loads((police_dir / result_filename(GID)).read_text())
    data["game_uid"] = "different-uid"
    (police_dir / result_filename(GID)).write_text(json.dumps(data))
    model = build_replay_view(police_dir, thief_dir)
    assert model.verification_ok is False
    assert any("game_uid" in f for f in model.police.findings)


def test_wrong_config_hash_is_detected(tmp_path) -> None:
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    data = json.loads((police_dir / config_filename(GID, 1)).read_text())
    data["config_sha256"] = "0" * 64
    (police_dir / config_filename(GID, 1)).write_text(json.dumps(data))
    model = build_replay_view(police_dir, thief_dir)
    assert model.verification_ok is False


def test_mismatched_score_is_detected(tmp_path) -> None:
    police_dir, thief_dir = tmp_path / "police", tmp_path / "thief"
    police_dir.mkdir()
    thief_dir.mkdir()
    _write_police_bundle(police_dir)
    _write_thief_bundle(thief_dir)
    data = json.loads((police_dir / result_filename(GID)).read_text())
    data["sub_games"][0]["police_score"] = 999
    (police_dir / result_filename(GID)).write_text(json.dumps(data))
    model = build_replay_view(police_dir, thief_dir)
    assert model.verification_ok is False


def test_no_dependency_on_live_process_memory(tmp_path) -> None:
    """build_replay_view takes only a Path -- it never reads any
    in-process runtime object, module-level game state, or gui_sink."""
    import inspect

    from police_peer.gui.replay_view_model import build_replay_view as f

    params = inspect.signature(f).parameters
    assert set(params) == {"police_dir", "thief_dir"}
    for p in params.values():
        assert p.annotation in (Path, "Path")

"""Batch 4A Task 7/8: headless tests for the graphical replay viewer's data
layer and playback navigation. No Tkinter import anywhere in this file.
Uses the SAME real artifact-writing helpers as
``tests/security/test_replay_verifier.py`` (Police's own crypto module) so
the "clean bundle" fixture is genuinely sealed/hashed, not hand-faked, and
Thief's fixture uses Thief's own real ``sealed-turn/2`` shape (a plain dict
this test constructs directly, mirroring real Thief artifacts observed in
Batch 4A's real GUI demo -- see integration_lab/evidence/batch4a/gui_demo/).
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


def _police_payload(sub_game: int, step: int) -> SealedTurnPayload:
    return SealedTurnPayload(
        step=step,
        role="police",
        sub_game_number=sub_game,
        state={"position": [step, 0]},
        move="S",
        barrier_placed=[2, 2] if step == 1 else None,
        intent="truth",
        hint="south looks fine",
        scent_digest="d" * 64,
        scent_grid=((0.0, 0.0), (0.0, 0.0)),
        capture_claim=(step, 0),
        claim_response=None,
        win_claim=False,
        timestamp="2026-07-18T00:00:00+00:00",
        nonce=f"{sub_game:032x}{step:032x}",
    )


def _write_police_bundle(directory: Path) -> None:
    with open(CONFIG_DIR / "game.json", encoding="utf-8") as handle:
        terms = json.load(handle)
    config_sha = sha256_hex(CONFIG_DIR / "game.json")
    for n in range(1, N_GAMES + 1):
        recs = tuple(
            SealedRecord(_police_payload(n, s), compute_commit_hash(_police_payload(n, s)))
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
    decl = {"schema_version": "declaration/1", "game_uid": UID, "game_id": GID, "role": "police"}
    (directory / f"declaration_{GID}.json").write_bytes(canonical_json_bytes(decl) + b"\n")


def _write_thief_bundle(directory: Path) -> None:
    """A real Thief-shaped bundle (string ``state``, ``sealed-turn/2``) --
    Thief's OWN crypto module is a different repo, so this test constructs
    the plain-dict artifact shape directly, matching real observed Thief
    output (see the module docstring)."""
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


def test_valid_six_sub_game_like_set_verified(tmp_path) -> None:
    model = _model(tmp_path)
    assert model.verdict == "VERIFIED"
    assert model.verification_ok is True
    assert len(model.sub_games) == N_GAMES


def test_thief_side_is_honestly_not_independently_verified(tmp_path) -> None:
    """The real cross-schema bug found while building this viewer: Police's
    own engine cannot correctly verify Thief's differently-shaped
    artifacts, so it must never claim VERIFIED or TAMPERED for that side."""
    model = _model(tmp_path)
    assert model.thief.independently_verified is False
    assert model.police.independently_verified is True


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

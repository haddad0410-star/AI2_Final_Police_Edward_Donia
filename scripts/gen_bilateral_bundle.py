"""Batch 4B Task 6: write a small, real, valid ``commitment/1`` Police
artifact bundle to a directory given as argv[1] -- dev/test tooling (like
``print_commitment_vector.py``), not part of the 150-line src/ cap, never
used at runtime by the real peer. Uses this repo's own crypto/artifact
modules for real (no hand-typed hashes), so the output is genuinely
self-verifiable by ``verify-replay``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from police_peer.domain.crypto import SealedRecord, SealedTurnPayload
from police_peer.domain.crypto.audit import AuditResult, AuditVerdict
from police_peer.domain.crypto.sealing import compute_commit_hash
from police_peer.services.artifact_builders import build_log_artifact
from police_peer.services.artifact_models import ConfigArtifact, ResultArtifact
from police_peer.services.artifacts import (
    config_filename,
    log_filename,
    result_filename,
    save_artifact,
)
from police_peer.shared.canonical_json import canonical_json_bytes
from police_peer.shared.config_loader import sha256_hex

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "police" / "game.json"
UID = "bilateral-0000-1111-2222-333344445555"
GID = "batch4b-bilateral"
N_GAMES = 2
STEPS = 3
CONFIG_SHA = sha256_hex(CONFIG_PATH)
TERMS = json.loads(CONFIG_PATH.read_text())


def _payload(sub_game: int, step: int) -> SealedTurnPayload:
    return SealedTurnPayload(
        step=step,
        role="police",
        sub_game_number=sub_game,
        position=(step, 0),
        move="S",
        barrier_placed=(2, 2) if step == 1 else None,
        intent="truth",
        hint="south corridor",
        scent_digest="a" * 8,
        scent_grid=((0.0, 0.0), (0.0, 0.0)),
        capture_claim=(step, 0) if step == STEPS - 1 else None,
        claim_response=None,
        win_claim=False,
        config_sha256=CONFIG_SHA,
        timestamp="2026-07-22T00:00:00+00:00",
        nonce=f"police-{sub_game}-{step}-fixed-nonce",
    )


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for n in range(1, N_GAMES + 1):
        recs = tuple(
            SealedRecord(p, compute_commit_hash(p)) for p in (_payload(n, s) for s in range(STEPS))
        )
        save_artifact(ConfigArtifact(UID, GID, n, CONFIG_SHA, TERMS), out / config_filename(GID, n))
        log = build_log_artifact(UID, GID, n, recs, AuditResult(AuditVerdict.VERIFIED, "ok"))
        save_artifact(log, out / log_filename(GID, n))
    sub_games = [
        {
            "sub_game_number": n,
            "result": "capture",
            "winner": "police",
            "police_score": 20,
            "thief_score": 5,
            "steps": STEPS,
            "audit_ok": True,
        }
        for n in range(1, N_GAMES + 1)
    ]
    result = ResultArtifact(
        game_uid=UID,
        game_id=GID,
        git_commit="deadbeef",
        group_id=GID,
        config_sha256=CONFIG_SHA,
        sub_games=sub_games,
        police_total=20 * N_GAMES,
        thief_total=5 * N_GAMES,
        agreement_status="agreed",
        agreed=True,
    )
    save_artifact(result, out / result_filename(GID))
    decl = {"schema_version": "declaration/1", "game_uid": UID, "game_id": GID, "role": "police"}
    (out / f"declaration_{GID}.json").write_bytes(canonical_json_bytes(decl) + b"\n")
    print(f"wrote bilateral Police bundle to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

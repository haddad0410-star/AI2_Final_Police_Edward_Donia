"""Filename derivation, canonical save/load, and cross-artifact checks.

Filenames are ALWAYS derived from ``game_id`` programmatically -- never
hand-typed -- so files from different games cannot be mixed. Every save
validates the model and scans for accidental credentials; every load validates
the parsed schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from police_peer.shared.canonical_json import canonical_json_bytes
from police_peer.shared.errors import SchemaValidationError

#: Substrings that must never appear as VALUES in a published artifact.
_CREDENTIAL_NEEDLES = (
    "password",
    "api_key",
    "apikey",
    "client_secret",
    "credentials.json",
    "token.json",
    "-----begin",
)


class _Artifact(Protocol):
    def to_dict(self) -> dict[str, Any]: ...
    def validate(self) -> None: ...


def declaration_filename(game_id: str) -> str:
    return f"declaration_{game_id}.json"


def config_filename(game_id: str, sub_game_number: int) -> str:
    return f"config_{game_id}_g{sub_game_number:02d}.json"


def log_filename(game_id: str, sub_game_number: int) -> str:
    return f"log_{game_id}_g{sub_game_number:02d}.json"


def result_filename(game_id: str) -> str:
    return f"result_{game_id}.json"


def assert_no_credentials(data: dict) -> None:
    """Raise if any credential-like substring appears in the serialized artifact."""
    serialized = json.dumps(data).lower()
    for needle in _CREDENTIAL_NEEDLES:
        if needle in serialized:
            raise SchemaValidationError(f"artifact appears to contain a secret: {needle!r}")


def save_artifact(artifact: _Artifact, path: Path) -> Path:
    """Validate, scan for secrets, and write canonical JSON to ``path``."""
    artifact.validate()
    data = artifact.to_dict()
    assert_no_credentials(data)
    path.write_bytes(canonical_json_bytes(data) + b"\n")
    return path


def load_json(path: Path) -> dict:
    """Read and parse an artifact file as a JSON object."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SchemaValidationError(f"artifact {path} is not a JSON object")
    return data


def assert_consistent_game_uid(*artifacts: dict) -> str:
    """Return the shared ``game_uid`` across all artifacts, or raise on mismatch."""
    uids = {a.get("game_uid") for a in artifacts}
    if len(uids) != 1 or None in uids:
        raise SchemaValidationError(f"artifacts do not share one game_uid: {uids}")
    return uids.pop()

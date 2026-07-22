"""Batch 4B Task 5: print the canonical JSON + SHA-256 for one commitment
test vector, read as JSON from stdin.

Dev/test tooling only (like ``check_file_lengths.py``), not part of the
150-line src/ cap. Never used at runtime by the real peer -- it exists so
``integration_lab`` can drive both repos' OWN crypto modules from separate
OS processes and compare their outputs, without either repo importing the
other or integration_lab importing either repo's production code.

Input JSON keys map 1:1 onto ``SealedTurnPayload`` fields. Optional keys
default to their normal dataclass defaults.
"""

from __future__ import annotations

import json
import sys

from police_peer.domain.crypto.payload import SealedTurnPayload
from police_peer.domain.crypto.sealing import compute_commit_hash
from police_peer.shared.canonical_json import canonical_json_bytes


def main() -> int:
    vector = json.loads(sys.stdin.read())
    kwargs = dict(vector)
    for key in ("position", "barrier_placed", "capture_claim"):
        if kwargs.get(key) is not None:
            kwargs[key] = tuple(kwargs[key])
    if "scent_grid" in kwargs:
        kwargs["scent_grid"] = tuple(tuple(row) for row in kwargs["scent_grid"])
    payload = SealedTurnPayload(**kwargs)
    canonical = canonical_json_bytes(payload.to_canonical_dict())
    result = {
        "canonical_json_hex": canonical.hex(),
        "sha256": compute_commit_hash(payload),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

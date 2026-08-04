"""Optional local-only diagnostic trace hook (Batch 3.5, Task 3/11).

Active only when the ``POLICE_TRACE_FILE`` environment variable is set. Never
sent over the wire, never given to the strategy, never affects gameplay --
purely an append-only JSONL diagnostic log of this peer's OWN turn-local
values (never the opponent's true position), used to prove or disprove
observation-pipeline defects. See ``observation_pipeline_audit.md``
(development-workspace evidence, not included in this standalone package).
"""

from __future__ import annotations

import json
import os
from typing import Any

from police_peer.domain.belief_model import BeliefMap, entropy, top_k
from police_peer.domain.scent import ScentField


def enabled() -> bool:
    return bool(os.environ.get("POLICE_TRACE_FILE"))


def belief_summary(belief: BeliefMap, k: int = 5) -> dict[str, Any]:
    return {
        "entropy": entropy(belief),
        "top_k": [[pos.row, pos.col, round(prob, 8)] for pos, prob in top_k(belief, k)],
    }


def scent_summary(scent: ScentField) -> dict[str, Any]:
    flat = [v for row in scent.grid for v in row]
    return {
        "dims": [scent.grid_size, scent.grid_size],
        "sum": round(sum(flat), 8),
        "min": round(min(flat), 8) if flat else None,
        "max": round(max(flat), 8) if flat else None,
    }


def record(event: dict[str, Any]) -> None:
    path = os.environ.get("POLICE_TRACE_FILE")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, default=str) + "\n")


def record_decide_turn(
    *, state, belief_before: BeliefMap, brain, decision, intent, hint, new_scent
) -> None:
    if not enabled():
        return
    record(
        {
            "event": "decide_turn",
            "step": state.step,
            "sub_game_number": state.sub_game_number,
            "belief_before": belief_summary(belief_before),
            "belief_after_advance": belief_summary(state.belief),
            "received_scent": scent_summary(state.received_scent),
            "hint_trust": state.hint_trust,
            "strategy_class": type(brain).__module__ + "." + type(brain).__qualname__,
            "action_selected": decision.direction.value,
            "barrier_chosen": [decision.barrier.row, decision.barrier.col]
            if decision.barrier
            else None,
            "outgoing_hint": hint.text,
            "outgoing_hint_intent": intent.value,
            "local_emitted_scent": scent_summary(new_scent),
        }
    )


def record_turn_exchange(*, state, commit_hash: str, payload, opponent) -> None:
    if not enabled():
        return
    record(
        {
            "event": "turn_exchange",
            "step": state.step,
            "sub_game_number": state.sub_game_number,
            "commit_hash": commit_hash,
            "outgoing_payload_keys": sorted(payload.to_canonical_dict().keys()),
            "received_message_type": "reveal",
            "received_scent_after_ingest": scent_summary(state.received_scent),
            "received_scent_valid": state.received_scent_valid,
            "received_hint": opponent.hint,
            "hint_region_decoded": state.hint_region is not None,
            "belief_after_ingest": belief_summary(state.belief),
        }
    )

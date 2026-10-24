"""Design matrix construction for the confirmatory analysis."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def build_design_matrix(trial_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a structured design matrix from trial-level data.

    Returns column specifications and the data ready for model fitting.
    """
    rows: list[dict[str, Any]] = []
    for t in trial_data:
        row = {
            "participant_id": t["participant_id"],
            "condition": t["condition"],
            "session_index": t.get("session_index", 0),
            "trial_index": t.get("trial_index", 0),
            "period": t.get("period", t.get("session_index", 0)),
            "composite_error": t["composite_error"],
            "baseline_precision": t.get("baseline_precision", 0.5),
            "task_family": t.get("task_family", "feature_reconstruction"),
            "carryover_indicator": t.get("carryover_indicator", "none"),
        }
        if "vividness" in t:
            row["vividness"] = t["vividness"]
        if "confidence" in t:
            row["confidence"] = t["confidence"]
        rows.append(row)

    return {
        "columns": list(rows[0].keys()) if rows else [],
        "n_rows": len(rows),
        "n_participants": len({r["participant_id"] for r in rows}),
        "n_conditions": len({r["condition"] for r in rows}),
        "rows": rows,
    }


def design_matrix_hash(dm: dict[str, Any]) -> str:
    canon = json.dumps(
        {"columns": dm["columns"], "n_rows": dm["n_rows"]},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode()).hexdigest()

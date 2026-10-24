"""Versioned practice protocols for the Imagination Instrument.

Protocols describe a bounded behavioural session: how many trials, which task families, and when to stop.
They do not encode treatment claims or adaptive thresholds that have not been validated. The built-ins are
starting points for usability research, not evidence-based prescriptions.
"""
from __future__ import annotations

from typing import Any

from app.core.animus.studio.profile import DIMENSION_SPECS
from app.core.animus.studio.tasks import TASK_TYPES

PROTOCOL_VERSION = "ANIMUS-PROTOCOL-v1"

BUILTIN_PROTOCOLS: tuple[dict[str, Any], ...] = (
    {
        "protocol_id": "core-calibration-12",
        "version": PROTOCOL_VERSION,
        "name": "Core calibration · 12 trials",
        "description": "A short mixed session for a first behavioural profile. Suggested, not validated.",
        "builtin": True,
        "spec": {
            "total_trials": 12,
            "max_minutes": 15,
            "task_types": [
                "attribute_recall", "candidate_discrimination", "spatial_view",
                "control_choice", "style_recall",
            ],
            "dimensions": ["stability", "discrimination", "spatial", "control", "calibration"],
            "stopping": {"max_consecutive_errors": 5, "fatigue_prompt": True},
        },
    },
    {
        "protocol_id": "stability-8",
        "version": PROTOCOL_VERSION,
        "name": "Recall stability · 8 trials",
        "description": "Repeated scene-detail recall with confidence ratings.",
        "builtin": True,
        "spec": {
            "total_trials": 8,
            "max_minutes": 10,
            "task_types": ["attribute_recall", "style_recall"],
            "dimensions": ["stability", "calibration"],
            "stopping": {"max_consecutive_errors": 4, "fatigue_prompt": True},
        },
    },
    {
        "protocol_id": "spatial-8",
        "version": PROTOCOL_VERSION,
        "name": "Viewpoint control · 8 trials",
        "description": "Short spatial transformation practice on the current scene.",
        "builtin": True,
        "spec": {
            "total_trials": 8,
            "max_minutes": 10,
            "task_types": ["spatial_view"],
            "dimensions": ["spatial", "calibration"],
            "stopping": {"max_consecutive_errors": 4, "fatigue_prompt": True},
        },
    },
)


def validate_protocol(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("protocol must be an object")
    required = {"protocol_id", "version", "name", "spec"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"protocol is missing {sorted(missing)[0]}")
    unknown = set(payload) - {"protocol_id", "version", "name", "description", "builtin", "spec"}
    if unknown:
        raise ValueError(f"protocol has unknown field {sorted(unknown)[0]}")
    if payload["version"] != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol version")
    spec = payload["spec"]
    if not isinstance(spec, dict):
        raise ValueError("protocol spec must be an object")
    unknown_spec = set(spec) - {
        "total_trials", "max_minutes", "task_types", "dimensions", "stopping", "difficulty",
    }
    if unknown_spec:
        raise ValueError(f"protocol spec has unknown field {sorted(unknown_spec)[0]}")
    total = int(spec.get("total_trials") or 0)
    if not 1 <= total <= 60:
        raise ValueError("total_trials must be between 1 and 60")
    if int(spec.get("max_minutes") or 0) not in range(1, 61):
        raise ValueError("max_minutes must be between 1 and 60")
    dimensions = spec.get("dimensions") or []
    if not isinstance(dimensions, list) or any(name not in DIMENSION_SPECS for name in dimensions):
        raise ValueError("protocol dimensions must be known measurement dimensions")
    task_types = spec.get("task_types") or []
    if not isinstance(task_types, list) or any(name not in TASK_TYPES for name in task_types):
        raise ValueError("protocol task_types must be known practice tasks")
    difficulty = spec.get("difficulty")
    if difficulty is not None:
        if not isinstance(difficulty, dict):
            raise ValueError("protocol difficulty must be an object")
        try:
            low = float(difficulty["min"])
            high = float(difficulty["max"])
            start = float(difficulty["start"])
            step = float(difficulty["step"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("protocol difficulty requires numeric start/min/max/step") from exc
        if not 0.05 <= low < high <= 0.95:
            raise ValueError("protocol difficulty bounds must be inside 0.05..0.95")
        if not low <= start <= high:
            raise ValueError("protocol start difficulty must be inside its bounds")
        if not 0.01 <= step <= 0.25:
            raise ValueError("protocol difficulty step must be between 0.01 and 0.25")
    return payload


def protocol_summary(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": protocol["protocol_id"],
        "version": protocol["version"],
        "name": protocol["name"],
        "description": protocol.get("description", ""),
        "builtin": bool(protocol.get("builtin")),
        "total_trials": int((protocol.get("spec") or {}).get("total_trials") or 0),
        "max_minutes": int((protocol.get("spec") or {}).get("max_minutes") or 0),
        "dimensions": list((protocol.get("spec") or {}).get("dimensions") or []),
    }


__all__ = ["PROTOCOL_VERSION", "BUILTIN_PROTOCOLS", "validate_protocol", "protocol_summary"]

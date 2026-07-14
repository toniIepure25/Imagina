"""Objective measurement session integration with the persistent runtime.

Extends the existing research runtime to support objective psychophysics
task types while preventing evaluation leakage into the adaptive policy.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.research.objective_endpoints import REGISTRY_VERSION, registry_hash
from app.research.psychophysics.calibration import CALIBRATION_VERSION
from app.research.psychophysics.common import BATTERY_VERSION, TaskFamily
from app.research.psychophysics.scoring import SCORING_VERSION

OBJECTIVE_RUNTIME_VERSION = "1.0"

TASK_TYPES = {
    "imagery_reconstruction": TaskFamily.FEATURE_RECONSTRUCTION,
    "imagery_manipulation": TaskFamily.IMAGERY_MANIPULATION,
    "imagery_stability": TaskFamily.DELAYED_IMAGERY,
    "perceptual_control": TaskFamily.PERCEPTUAL_CONTROL,
    "self_report": None,
}


def manifest_objective_fields(
    calibration_hash: str | None = None,
    trial_schedule_hash: str | None = None,
    analysis_spec_hash: str | None = None,
    agent_model_version: str | None = None,
) -> dict[str, str | None]:
    """Return objective measurement fields for manifest integration."""
    return {
        "objective_battery_version": BATTERY_VERSION,
        "endpoint_registry_version": REGISTRY_VERSION,
        "endpoint_registry_hash": registry_hash(),
        "task_generator_version": BATTERY_VERSION,
        "scoring_version": SCORING_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "calibration_hash": calibration_hash,
        "trial_schedule_hash": trial_schedule_hash,
        "analysis_specification_hash": analysis_spec_hash,
        "cognitive_agent_model_version": agent_model_version,
        "objective_runtime_version": OBJECTIVE_RUNTIME_VERSION,
    }


def serialize_trial_record(
    trial_id: str,
    task_family: str,
    stimulus_spec: dict[str, Any],
    target_features: dict[str, float],
    transform_spec: dict[str, Any] | None,
    response_features: dict[str, float],
    component_errors: dict[str, float],
    composite_score: float,
    response_latency_ms: float,
    confidence: float | None,
    vividness: float | None,
    effort: float | None,
    invalidity_flags: list[str],
    phase_timestamps: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Serialize a single objective trial record for persistence."""
    return {
        "trial_id": trial_id,
        "task_family": task_family,
        "stimulus_spec": stimulus_spec,
        "target_features": target_features,
        "transform_spec": transform_spec,
        "response_features": response_features,
        "component_errors": component_errors,
        "composite_endpoint_score": composite_score,
        "response_latency_ms": response_latency_ms,
        "confidence": confidence,
        "vividness": vividness,
        "effort": effort,
        "invalidity_flags": invalidity_flags,
        "scoring_version": SCORING_VERSION,
        "task_generator_version": BATTERY_VERSION,
        "phase_timestamps": phase_timestamps,
    }


class LeakageGuard:
    """Prevents objective evaluation outcomes from leaking into the adaptive policy.

    The adaptive feedback policy receives only online adaptation signals
    (IQI, PID, state estimates). It must never receive composite_endpoint_score,
    component_errors, or any objective trial outcome before that trial is finalized.
    """

    def __init__(self) -> None:
        self._finalized_trials: set[str] = set()
        self._reserved_fields = {
            "composite_endpoint_score", "component_errors",
            "composite_error", "orientation_error", "hue_error",
            "spatial_frequency_error", "position_error", "size_error",
        }

    def finalize_trial(self, trial_id: str) -> None:
        self._finalized_trials.add(trial_id)

    def check_policy_input(self, context: dict[str, Any]) -> list[str]:
        """Return list of leaked field names, empty if clean."""
        violations: list[str] = []
        for field in self._reserved_fields:
            if field in context:
                violations.append(field)
        for key in context:
            if key.startswith("objective_") and key != "objective_battery_version":
                violations.append(key)
        return violations

    def is_trial_finalized(self, trial_id: str) -> bool:
        return trial_id in self._finalized_trials


def compute_objective_manifest_hash(
    fields: dict[str, str | None],
) -> str:
    """Compute a deterministic hash of all objective manifest fields."""
    canon = json.dumps(
        {k: v for k, v in sorted(fields.items()) if v is not None},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode()).hexdigest()

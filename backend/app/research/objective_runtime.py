"""Objective measurement session integration with the persistent runtime.

Extends the existing research runtime to support objective psychophysics
task types while preventing evaluation leakage into the adaptive policy.
Includes the objective session executor for running task blocks through
the persistent runtime with LeakageGuard enforcement.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.objective_endpoints import (
    REGISTRY_VERSION,
    registry_hash,
)
from app.research.psychophysics.calibration import CALIBRATION_VERSION
from app.research.psychophysics.common import BATTERY_VERSION, StimulusSpec, TaskFamily
from app.research.psychophysics.scoring import SCORING_VERSION
from app.research.rng_registry import derive_seed

OBJECTIVE_RUNTIME_VERSION = "2.0"

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
        for fname in self._reserved_fields:
            if fname in context:
                violations.append(fname)
        for key in context:
            if key.startswith("objective_") and key != "objective_battery_version":
                violations.append(key)
        return violations

    def is_trial_finalized(self, trial_id: str) -> bool:
        return trial_id in self._finalized_trials


class OutcomeLeakageError(Exception):
    """Raised when objective outcomes leak into the adaptive policy path."""


@dataclass
class LeakageAuditRecord:
    trial_id: str
    policy_input_fields: list[str]
    forbidden_fields_checked: list[str]
    violations: list[str]
    outcome_finalization_time: str | None = None
    policy_decision_time: str | None = None
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ObjectiveTrialResult:
    trial_id: str
    task_family: str
    target: dict[str, Any]
    response: dict[str, Any]
    component_errors: dict[str, float]
    composite_error: float
    confidence: float
    vividness: float
    effort: float
    latency_ms: float
    scoring_version: str = SCORING_VERSION
    endpoint_registry_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ObjectiveSessionResult:
    session_id: str
    participant_id: str
    condition: str
    period: int
    trials: list[ObjectiveTrialResult] = field(default_factory=list)
    leakage_audit: list[LeakageAuditRecord] = field(default_factory=list)
    manifest_hash: str = ""
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "condition": self.condition,
            "period": self.period,
            "n_trials": len(self.trials),
            "trials": [t.to_dict() for t in self.trials],
            "leakage_audit": [a.to_dict() for a in self.leakage_audit],
            "manifest_hash": self.manifest_hash,
            "content_hash": self.content_hash,
        }


def execute_objective_session(
    session_id: str,
    participant_id: str,
    condition: str,
    period: int,
    trial_specs: list[dict[str, Any]],
    response_provider: Any,
    leakage_guard: LeakageGuard,
    seed: int,
    prev_condition: str | None = None,
) -> ObjectiveSessionResult:
    """Execute an objective task block through the persistent runtime.

    Each trial is checked for leakage BEFORE finalizing. If an
    OutcomeLeakageError is raised, no trial result is recorded.
    """
    result = ObjectiveSessionResult(
        session_id=session_id,
        participant_id=participant_id,
        condition=condition,
        period=period,
    )
    reg_hash = registry_hash()

    for spec in trial_specs:
        trial_id = f"{session_id}-t{spec['trial_index']}-{spec['task_family']}"
        target = StimulusSpec(
            orientation_deg=spec.get("target_orientation", 45),
            hue_deg=spec.get("target_hue", 120),
            spatial_frequency_cpd=spec.get("target_sf", 3.0),
            position_x=spec.get("target_pos_x", 500),
            position_y=spec.get("target_pos_y", 400),
            size=spec.get("target_size", 50),
        )

        trial_seed = derive_seed(seed, "simulation",
                                  participant_id=participant_id,
                                  session_index=period,
                                  trial_index=spec["trial_index"])

        resp = response_provider.generate_response(
            target=target,
            expected=target,
            condition=condition,
            session_index=period,
            trial_index=spec["trial_index"],
            is_perceptual_control=spec.get("is_perceptual_control", False),
            seed=trial_seed,
            delay_s=spec.get("delay_s", 0.0),
            prev_condition=prev_condition,
        )

        comp_errors = resp.get("component_errors", {})
        composite = resp.get("composite_error", 0.0)

        policy_context = {"condition": condition, "period": period, "session_id": session_id}
        violations = leakage_guard.check_policy_input(policy_context)
        audit = LeakageAuditRecord(
            trial_id=trial_id,
            policy_input_fields=list(policy_context.keys()),
            forbidden_fields_checked=list(leakage_guard._reserved_fields),
            violations=violations,
            passed=len(violations) == 0,
        )

        if violations:
            result.leakage_audit.append(audit)
            raise OutcomeLeakageError(
                f"Objective outcomes leaked into policy context: {violations}"
            )

        leakage_guard.finalize_trial(trial_id)
        result.leakage_audit.append(audit)

        trial_result = ObjectiveTrialResult(
            trial_id=trial_id,
            task_family=spec["task_family"],
            target=target.to_dict(),
            response=resp.get("response", {}),
            component_errors=comp_errors,
            composite_error=composite,
            confidence=resp.get("confidence", 0),
            vividness=resp.get("vividness", 0),
            effort=resp.get("effort", 0),
            latency_ms=resp.get("latency_ms", 0),
            endpoint_registry_hash=reg_hash,
        )
        result.trials.append(trial_result)

    content = json.dumps(
        [t.to_dict() for t in result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    result.content_hash = hashlib.sha256(content.encode()).hexdigest()
    result.manifest_hash = compute_objective_manifest_hash(manifest_objective_fields())

    return result


async def execute_objective_session_persistent(
    db,
    session_id: str,
    participant_id: str,
    condition: str,
    period: int,
    trial_specs: list[dict[str, Any]],
    response_provider: Any,
    leakage_guard: LeakageGuard,
    seed: int,
    prev_condition: str | None = None,
) -> ObjectiveSessionResult:
    """Execute objective tasks with transactional DB persistence.

    Each trial is persisted atomically: spec, response, scores, audit,
    and transition in one transaction. On leakage, the transaction
    rolls back leaving no rows.
    """
    reg_hash = registry_hash()
    result = ObjectiveSessionResult(
        session_id=session_id,
        participant_id=participant_id,
        condition=condition,
        period=period,
    )

    await db.execute("BEGIN")
    try:
        block_cursor = await db.execute(
            """INSERT INTO objective_task_blocks
               (study_id, session_id, participant_id, period, condition,
                task_family, block_index, schedule_hash)
               VALUES (?, ?, ?, ?, ?, 'mixed', 0, ?)""",
            (session_id, session_id, participant_id, period, condition,
             hashlib.sha256(json.dumps(trial_specs, sort_keys=True).encode()).hexdigest()[:16]),
        )
        block_id = block_cursor.lastrowid

        for spec in trial_specs:
            trial_id = f"{session_id}-t{spec['trial_index']}-{spec['task_family']}"
            target = StimulusSpec(
                orientation_deg=spec.get("target_orientation", 45),
                hue_deg=spec.get("target_hue", 120),
                spatial_frequency_cpd=spec.get("target_sf", 3.0),
                position_x=spec.get("target_pos_x", 500),
                position_y=spec.get("target_pos_y", 400),
                size=spec.get("target_size", 50),
            )

            trial_seed = derive_seed(seed, "simulation",
                                      participant_id=participant_id,
                                      session_index=period,
                                      trial_index=spec["trial_index"])

            resp = response_provider.generate_response(
                target=target, expected=target, condition=condition,
                session_index=period, trial_index=spec["trial_index"],
                is_perceptual_control=spec.get("is_perceptual_control", False),
                seed=trial_seed, delay_s=spec.get("delay_s", 0.0),
                prev_condition=prev_condition,
            )

            comp_errors = resp.get("component_errors", {})
            composite = resp.get("composite_error", 0.0)

            policy_context = {"condition": condition, "period": period, "session_id": session_id}
            violations = leakage_guard.check_policy_input(policy_context)
            audit = LeakageAuditRecord(
                trial_id=trial_id,
                policy_input_fields=list(policy_context.keys()),
                forbidden_fields_checked=list(leakage_guard._reserved_fields),
                violations=violations,
                passed=len(violations) == 0,
            )

            if violations:
                await db.execute("ROLLBACK")
                result.leakage_audit.append(audit)
                raise OutcomeLeakageError(
                    f"Leakage detected — session transaction rolled back: {violations}"
                )

            spec_cursor = await db.execute(
                """INSERT INTO objective_trial_specs
                   (block_id, trial_index, task_family, target_orientation,
                    target_hue, target_sf, target_pos_x, target_pos_y,
                    target_size, delay_s, is_perceptual_control)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (block_id, spec["trial_index"], spec["task_family"],
                 target.orientation_deg, target.hue_deg, target.spatial_frequency_cpd,
                 target.position_x, target.position_y, target.size,
                 spec.get("delay_s", 0.0), int(spec.get("is_perceptual_control", False))),
            )
            trial_spec_id = spec_cursor.lastrowid

            r = resp.get("response", {})
            resp_cursor = await db.execute(
                """INSERT INTO objective_trial_responses
                   (trial_spec_id, response_orientation, response_hue,
                    response_sf, response_pos_x, response_pos_y,
                    response_size, latency_ms, confidence,
                    vividness, effort)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trial_spec_id,
                 r.get("orientation_deg", 0), r.get("hue_deg", 0),
                 r.get("spatial_frequency_cpd", 0), r.get("position_x", 0),
                 r.get("position_y", 0), r.get("size", 0),
                 resp.get("latency_ms", 0), resp.get("confidence", 0),
                 resp.get("vividness", 0), resp.get("effort", 0)),
            )
            response_id = resp_cursor.lastrowid

            await db.execute(
                """INSERT INTO objective_trial_scores
                   (response_id, scoring_version, endpoint_registry_hash,
                    orientation_error, hue_error, sf_error, position_error,
                    size_error, composite_error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (response_id, SCORING_VERSION, reg_hash,
                 comp_errors.get("orientation", 0), comp_errors.get("hue", 0),
                 comp_errors.get("spatial_frequency", 0), comp_errors.get("position", 0),
                 comp_errors.get("size", 0), composite),
            )

            await db.execute(
                """INSERT INTO objective_leakage_audits
                   (block_id, trial_id, passed, violations, policy_fields, checked_fields)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (block_id, trial_id, int(audit.passed),
                 json.dumps(audit.violations), json.dumps(audit.policy_input_fields),
                 json.dumps(audit.forbidden_fields_checked)),
            )

            leakage_guard.finalize_trial(trial_id)
            result.leakage_audit.append(audit)

            trial_result = ObjectiveTrialResult(
                trial_id=trial_id,
                task_family=spec["task_family"],
                target=target.to_dict(),
                response=r,
                component_errors=comp_errors,
                composite_error=composite,
                confidence=resp.get("confidence", 0),
                vividness=resp.get("vividness", 0),
                effort=resp.get("effort", 0),
                latency_ms=resp.get("latency_ms", 0),
                endpoint_registry_hash=reg_hash,
            )
            result.trials.append(trial_result)

        await db.execute("COMMIT")
    except OutcomeLeakageError:
        raise
    except Exception:
        await db.execute("ROLLBACK")
        raise

    content = json.dumps(
        [t.to_dict() for t in result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    result.content_hash = hashlib.sha256(content.encode()).hexdigest()
    result.manifest_hash = compute_objective_manifest_hash(manifest_objective_fields())

    return result


def compute_objective_manifest_hash(
    fields: dict[str, str | None],
) -> str:
    """Compute a deterministic hash of all objective manifest fields."""
    canon = json.dumps(
        {k: v for k, v in sorted(fields.items()) if v is not None},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode()).hexdigest()

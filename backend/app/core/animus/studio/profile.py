"""Behavioral profile for the ANIMUS Imagination Instrument.

This module deliberately estimates *task behaviour*, not imagery strength, neural content, personality, or
clinical status. Each dimension has its own posterior summary and the UI must show the evidence count and
uncertainty. There is no composite "imagination score": combining weakly correlated measurements into one
number would manufacture precision the instrument does not have.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

PROFILE_ID = "local_default"
PROFILE_VERSION = "ANIMUS-PROFILE-v1"
MIN_REPORTED_TRIALS = 3

DIMENSION_SPECS: dict[str, dict[str, Any]] = {
    "stability": {
        "label": "Object detail",
        "description": "How fully you reconstruct objects and attributes after the scene is hidden.",
        "task_types": ["object_reconstruction", "attribute_recall", "style_recall"],
        "construct": "behavioral_object_reconstruction",
    },
    "discrimination": {
        "label": "Scene discrimination",
        "description": "How well you distinguish a described scene from a close alternative.",
        "task_types": ["candidate_discrimination"],
        "construct": "behavioral_scene_discrimination",
    },
    "spatial": {
        "label": "Spatial structure",
        "description": "How accurately you reconstruct layout and identify a viewpoint change.",
        "task_types": ["spatial_layout", "spatial_view"],
        "construct": "behavioral_spatial_reconstruction",
    },
    "control": {
        "label": "Edit control",
        "description": "How reliably you choose the edit that achieves a stated scene goal.",
        "task_types": ["control_choice"],
        "construct": "behavioral_edit_control",
    },
    "calibration": {
        "label": "Confidence calibration",
        "description": "How closely your stated confidence tracks your actual task accuracy.",
        "task_types": ["object_reconstruction", "spatial_layout", "attribute_recall", "style_recall",
                       "candidate_discrimination", "spatial_view", "control_choice"],
        "construct": "metacognitive_calibration",
    },
}

LIMITATIONS = (
    "These are experimental behavioural estimates from local practice trials, not a diagnosis or a fixed trait.",
    "A dimension with fewer than three trials is not reported as an estimate.",
    "Scores describe performance on these scene tasks; they do not measure neural imagery or general intelligence.",
    "No clinical, far-transfer, or imagery-strength claim is authorized.",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_stats() -> dict[str, Any]:
    return {"alpha": 1.0, "beta": 1.0, "brier_sum": 0.0, "brier_n": 0, "last_score": None}


def empty_error_signature() -> dict[str, Any]:
    return {
        "n": 0,
        "omissions": 0,
        "intrusions": 0,
        "mean_spatial_error": None,
        "spatial_n": 0,
        "epistemic_n": 0,
    }


def error_signature_from_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    signature = empty_error_signature()
    spatial_total = 0.0
    for trial in trials:
        outcome = trial.get("outcome") if isinstance(trial, dict) else None
        if not isinstance(outcome, dict) or outcome.get("response_kind") == "option":
            continue
        if outcome.get("response_kind") == "probability_choice":
            signature["epistemic_n"] += 1
            continue
        profile = outcome.get("error_profile")
        if not isinstance(profile, dict):
            continue
        signature["n"] += 1
        signature["omissions"] += max(0, int(profile.get("omissions") or 0))
        signature["intrusions"] += max(0, int(profile.get("intrusions") or 0))
        spatial_n = max(0, int(profile.get("spatial_n") or 0))
        if spatial_n:
            spatial_total += float(profile.get("mean_spatial_error") or 0.0) * spatial_n
            signature["spatial_n"] += spatial_n
    if signature["spatial_n"]:
        signature["mean_spatial_error"] = round(spatial_total / signature["spatial_n"], 4)
    return signature


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def apply_observation(stats: dict[str, Any] | None, *, score: float,
                      confidence: float | None = None) -> dict[str, Any]:
    """Update sufficient statistics with one trial.

    ``score`` is in [0, 1]. Beta-Binomial updating is used for ability dimensions because it is
    transparent, bounded, and does not pretend to be a validated IRT model. Calibration is tracked as a
    Brier score and is intentionally kept separate from ability.
    """
    out = {**empty_stats(), **(stats or {})}
    value = max(0.0, min(1.0, _finite(score)))
    out["alpha"] = max(0.001, _finite(out.get("alpha"), 1.0)) + value
    out["beta"] = max(0.001, _finite(out.get("beta"), 1.0)) + (1.0 - value)
    out["last_score"] = value
    if confidence is not None:
        stated = max(0.0, min(1.0, _finite(confidence)))
        out["brier_sum"] = max(0.0, _finite(out.get("brier_sum"))) + (stated - value) ** 2
        out["brier_n"] = max(0, int(out.get("brier_n") or 0)) + 1
    return out


def estimate_from_stats(stats: dict[str, Any] | None) -> dict[str, Any]:
    payload = {**empty_stats(), **(stats or {})}
    alpha = max(0.001, _finite(payload.get("alpha"), 1.0))
    beta = max(0.001, _finite(payload.get("beta"), 1.0))
    total = alpha + beta
    mean = alpha / total
    variance = (alpha * beta) / (total * total * (total + 1.0))
    n = max(0, int(round(total - 2.0)))
    brier_n = max(0, int(payload.get("brier_n") or 0))
    brier_sum = max(0.0, _finite(payload.get("brier_sum")))
    return {
        "estimate": round(mean, 4) if n >= MIN_REPORTED_TRIALS else None,
        "uncertainty": round(math.sqrt(max(variance, 0.0)), 4),
        "n": n,
        "reliability": round(min(1.0, n / 12.0), 3),
        "brier_score": round(brier_sum / brier_n, 4) if brier_n else None,
        "brier_n": brier_n,
    }


def calibration_from_stats(stats: dict[str, Any] | None) -> dict[str, Any]:
    payload = {**empty_stats(), **(stats or {})}
    n = max(0, int(payload.get("brier_n") or 0))
    brier_sum = max(0.0, _finite(payload.get("brier_sum")))
    if n == 0:
        return {"estimate": None, "uncertainty": 1.0, "n": 0, "reliability": 0.0,
                "brier_score": None, "brier_n": 0}
    mean_brier = min(1.0, brier_sum / n)
    accuracy = max(0.0, 1.0 - mean_brier)
    variance = (accuracy * (1.0 - accuracy)) / (n + 1.0)
    return {
        "estimate": None,
        "uncertainty": round(math.sqrt(max(variance, 0.0)), 4),
        "n": n,
        "reliability": round(min(1.0, n / 12.0), 3),
        "brier_score": round(mean_brier, 4) if n >= MIN_REPORTED_TRIALS else None,
        "brier_n": n,
    }


def status_for(n: int) -> str:
    if n <= 0:
        return "no_evidence"
    if n < MIN_REPORTED_TRIALS:
        return "collecting"
    if n < 12:
        return "provisional"
    return "moderate_evidence"


def dimension_payload(dimension: str, stats: dict[str, Any] | None) -> dict[str, Any]:
    spec = DIMENSION_SPECS[dimension]
    estimate = calibration_from_stats(stats) if dimension == "calibration" else estimate_from_stats(stats)
    return {
        "id": dimension,
        "label": spec["label"],
        "description": spec["description"],
        "construct": spec["construct"],
        "estimate": estimate["estimate"],
        "uncertainty": estimate["uncertainty"],
        "n": estimate["n"],
        "reliability": estimate["reliability"],
        "status": status_for(estimate["n"]),
        "brier_score": estimate.get("brier_score") if dimension == "calibration" else None,
        "provenance": "BEHAVIORAL_PRACTICE",
    }


def empty_epistemic_summary() -> dict[str, Any]:
    return {
        "n_interviews": 0,
        "n_probes": 0,
        "mean_brier": None,
        "overconfidence": None,
        "abstention_rate": None,
        "mean_information_gain": None,
        "last_interview_id": None,
    }


def empty_contrast_summary() -> dict[str, Any]:
    return {
        "n_sessions": 0,
        "n_completed": 0,
        "n_trials": 0,
        "median_threshold": None,
        "mean_dprime": None,
        "mean_brier": None,
        "calibration_n": 0,
        "last_contrast_id": None,
    }


def profile_payload(profile: dict[str, Any], stats_by_dimension: dict[str, dict[str, Any]],
                    *, trial_count: int = 0,
                    error_signature: dict[str, Any] | None = None,
                    epistemic: dict[str, Any] | None = None,
                    contrast: dict[str, Any] | None = None) -> dict[str, Any]:
    dimensions = [dimension_payload(name, stats_by_dimension.get(name))
                  for name in DIMENSION_SPECS]
    return {
        "profile_id": profile.get("profile_id", PROFILE_ID),
        "profile_version": profile.get("profile_version", PROFILE_VERSION),
        "claim_level": "L1_BEHAVIORAL_ASSISTED",
        "privacy_scope": "local_only",
        "trial_count": max(0, int(trial_count)),
        "dimensions": dimensions,
        "error_signature": {**empty_error_signature(), **(error_signature or {})},
        "epistemic": {**empty_epistemic_summary(), **(epistemic or {})},
        "contrast": {**empty_contrast_summary(), **(contrast or {})},
        "limitations": list(LIMITATIONS),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "measured_at": _now(),
    }


def normalize_stats(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return empty_stats()
    return {
        **empty_stats(),
        **{key: raw[key] for key in ("alpha", "beta", "brier_sum", "brier_n", "last_score")
           if key in raw},
    }


__all__ = [
    "PROFILE_ID",
    "PROFILE_VERSION",
    "MIN_REPORTED_TRIALS",
    "DIMENSION_SPECS",
    "LIMITATIONS",
    "empty_stats",
    "empty_error_signature",
    "empty_epistemic_summary",
    "empty_contrast_summary",
    "error_signature_from_trials",
    "apply_observation",
    "estimate_from_stats",
    "calibration_from_stats",
    "status_for",
    "dimension_payload",
    "profile_payload",
    "normalize_stats",
]

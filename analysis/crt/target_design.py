"""Target-scale projection for the CRT confirmatory design.

A full N=432/T=240 fit of every candidate x model is too expensive for routine execution. This module
runs the full joint model at a pilot size, estimates the per-observation BIC separation, and projects
that separation to the target sample size with a normal approximation. The projection is explicitly
*not* a target-scale fit and cannot satisfy the target-scale SBC/recovery gate.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.stats import norm

from .design_optimization import DEFAULT_CANDIDATES, DesignCandidate
from .full_model import FULL_MODELS, FullModelConfig, fit_full_model, simulate_full_data

SCOPE = "target_scale_bic_projection_not_target_fit_or_human_evidence"
CONFIRMATORY = frozenset(FULL_MODELS)


@dataclass(frozen=True)
class TargetProjectionConfig:
    pilot_n: int = 12
    pilot_trials: int = 40
    target_n: int = 432
    target_trials: int = 240
    n_replicates: int = 1
    models: tuple[str, ...] = FULL_MODELS
    candidates: tuple[DesignCandidate, ...] = DEFAULT_CANDIDATES[:3]
    recovery_threshold: float = 0.85
    effect_scale: float = 0.8
    min_abs_effect: float = 0.25
    max_iter: int = 120
    seed: int = 20261031

    def __post_init__(self) -> None:
        if self.pilot_n < 6 or self.pilot_trials < 20:
            raise ValueError("pilot must have at least 6 participants and 20 trials")
        if self.target_n < self.pilot_n or self.target_trials < self.pilot_trials:
            raise ValueError("target must not be smaller than the pilot")
        if self.n_replicates <= 0:
            raise ValueError("n_replicates must be positive")
        if not self.models or any(model not in FULL_MODELS for model in self.models):
            raise ValueError("models must be a non-empty subset of FULL_MODELS")
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        if not 0 < self.recovery_threshold <= 1:
            raise ValueError("recovery_threshold must be in (0, 1]")

    @property
    def scale_factor(self) -> float:
        return (self.target_n * self.target_trials) / (self.pilot_n * self.pilot_trials)


def _delta_bic_rows(
    candidate: DesignCandidate,
    config: TargetProjectionConfig,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    rows: dict[str, list[np.ndarray]] = {model: [] for model in config.models}
    for true_model in config.models:
        for _ in range(config.n_replicates):
            seed = int(rng.integers(0, 2**31 - 1))
            data, _ = simulate_full_data(
                true_model,
                n_participants=config.pilot_n,
                n_trials=config.pilot_trials,
                seed=seed,
                effect_scale=config.effect_scale,
                min_abs_effect=config.min_abs_effect,
                predict_probability=candidate.predict_probability,
                dual_probability=candidate.dual_probability,
                vividness_spread=candidate.vividness_spread,
                confidence_spread=candidate.confidence_spread,
            )
            fits = [
                fit_full_model(
                    data,
                    model,
                    FullModelConfig(
                        n_participants=config.pilot_n,
                        n_trials=config.pilot_trials,
                        n_sbc=1,
                        n_posterior_draws=20,
                        n_recovery=1,
                        seed=seed,
                        max_iter=config.max_iter,
                    ),
                )
                for model in config.models
            ]
            true_index = config.models.index(true_model)
            rows[true_model].append(
                np.asarray([fit.bic - fits[true_index].bic for fit in fits], dtype=float)
            )
    return {model: np.asarray(values, dtype=float) for model, values in rows.items()}


def _projected_pairwise(
    deltas: dict[str, np.ndarray],
    models: tuple[str, ...],
    scale: float,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for left in range(len(models)):
        for right in range(left + 1, len(models)):
            a = models[left]
            b = models[right]
            # rows[a][:, right] is BIC_b - BIC_a under true a; rows[b][:, left] is BIC_a - BIC_b.
            mean_a = float(np.mean(deltas[a][:, right]))
            sd_a = float(np.std(deltas[a][:, right], ddof=1)) if len(deltas[a]) > 1 else 1.0
            mean_b = float(np.mean(deltas[b][:, left]))
            sd_b = float(np.std(deltas[b][:, left], ddof=1)) if len(deltas[b]) > 1 else 1.0
            z_a = math.sqrt(scale) * mean_a / max(sd_a, 1e-9)
            z_b = math.sqrt(scale) * mean_b / max(sd_b, 1e-9)
            result[f"{a}_vs_{b}"] = float((norm.cdf(z_a) + norm.cdf(z_b)) / 2.0)
    return result


def run_target_design_projection(config: TargetProjectionConfig | None = None) -> dict[str, Any]:
    cfg = config or TargetProjectionConfig()
    rng = np.random.default_rng(cfg.seed)
    rows: list[dict[str, Any]] = []
    for candidate in cfg.candidates:
        deltas = _delta_bic_rows(candidate, cfg, rng)
        pairwise = _projected_pairwise(deltas, tuple(cfg.models), cfg.scale_factor)
        minimum = min(pairwise.values()) if pairwise else 0.0
        rows.append(
            {
                "design_id": candidate.design_id,
                "candidate": asdict(candidate),
                "pairwise_projected_accuracy": pairwise,
                "min_pairwise_projected_accuracy": float(minimum),
                "pilot_delta_bic": {model: values.tolist() for model, values in deltas.items()},
            }
        )
    selected = max(rows, key=lambda row: row["min_pairwise_projected_accuracy"])
    complete = set(cfg.models) == CONFIRMATORY
    passed = complete and selected["min_pairwise_projected_accuracy"] >= cfg.recovery_threshold
    return {
        "analysis": "stage0i_target_design_projection",
        "scope": SCOPE,
        "method": "full_joint_model_pilot_bic_normal_projection",
        "models": list(cfg.models),
        "config": asdict(cfg),
        "scale_factor": cfg.scale_factor,
        "results": rows,
        "selected_design": selected,
        "decision": (
            "CRT_STAGE0I_TARGET_DESIGN_PROJECTION_PASS"
            if passed
            else "CRT_STAGE0I_TARGET_DESIGN_PROJECTION_REVIEW"
        ),
        "note": (
            "Projection from a pilot full-model fit to the target N/T. It is not a target-scale fit, "
            "not target-scale SBC, and not human evidence."
        ),
    }


def write_artifact(payload: dict[str, Any], path: Any) -> None:
    import json
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")

"""Offline design optimization for the CRT Stage 0H model-discrimination program.

The optimizer is deliberately a screening tool. It chooses a trial composition that makes the
confirmatory models disagree under simulation; it is not a hypothesis test and it never uses human
data. Final inference remains model-based (SBC, recovery, LOO/WAIC).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.stats import norm

from .full_model import FULL_MODELS, FullModelConfig, fit_full_model, simulate_full_data
from .trial_model import (
    CONFIRMATORY_MODELS,
    TrialModelConfig,
    fit_trial_model,
    simulate_trial_data,
)

SCOPE = "offline_model_discrimination_design_screening_not_human_evidence"
DEFAULT_MODELS: tuple[str, ...] = CONFIRMATORY_MODELS


@dataclass(frozen=True)
class DesignCandidate:
    design_id: str
    predict_probability: float
    dual_probability: float
    diagnosticity_low: float
    diagnosticity_high: float
    trials_per_cell: int = 25
    vividness_spread: float = 0.0
    confidence_spread: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.predict_probability <= 1.0:
            raise ValueError("predict_probability must be in [0, 1]")
        if not 0.0 <= self.dual_probability <= 1.0:
            raise ValueError("dual_probability must be in [0, 1]")
        if not 0.0 <= self.diagnosticity_low < self.diagnosticity_high <= 1.0:
            raise ValueError("diagnosticity bounds must be ordered within [0, 1]")
        if self.trials_per_cell <= 0:
            raise ValueError("trials_per_cell must be positive")
        if self.vividness_spread < 0 or self.confidence_spread < 0:
            raise ValueError("vividness_spread and confidence_spread must be non-negative")


DEFAULT_CANDIDATES: tuple[DesignCandidate, ...] = (
    DesignCandidate("balanced", 0.50, 0.50, 0.00, 1.00),
    DesignCandidate("high_diagnosticity", 0.50, 0.50, 0.60, 1.00),
    DesignCandidate("low_diagnosticity", 0.50, 0.50, 0.00, 0.40),
    DesignCandidate("vividness_manipulated", 0.50, 0.50, 0.00, 1.00, vividness_spread=0.35),
    DesignCandidate("confidence_manipulated", 0.50, 0.50, 0.00, 1.00, confidence_spread=0.35),
    DesignCandidate(
        "combined_manipulation",
        0.50,
        0.50,
        0.00,
        1.00,
        vividness_spread=0.35,
        confidence_spread=0.35,
    ),
    DesignCandidate("dual_heavy", 0.50, 0.75, 0.00, 1.00),
    DesignCandidate("dual_light", 0.50, 0.25, 0.00, 1.00),
    DesignCandidate("prediction_heavy", 0.75, 0.50, 0.00, 1.00),
    DesignCandidate("prediction_light", 0.25, 0.50, 0.00, 1.00),
)


@dataclass(frozen=True)
class DesignOptimizationConfig:
    n_participants: int = 16
    n_trials: int = 80
    n_replicates: int = 3
    n_power_simulations: int = 400
    models: tuple[str, ...] = DEFAULT_MODELS
    candidates: tuple[DesignCandidate, ...] = DEFAULT_CANDIDATES
    sesoi_d: float = 0.20
    main_n: int = 480
    analysed_n: int = 432
    power_threshold: float = 0.90
    discrimination_threshold: float = 0.85
    effect_scale: float = 0.8
    min_abs_effect: float = 0.25
    seed: int = 20261031
    laplace: bool = True

    def __post_init__(self) -> None:
        if self.n_participants < 6:
            raise ValueError("n_participants must be at least 6")
        if self.n_trials < 20:
            raise ValueError("n_trials must be at least 20")
        if self.n_replicates <= 0 or self.n_power_simulations <= 0:
            raise ValueError("simulation counts must be positive")
        if len(self.models) < 2 or any(model not in CONFIRMATORY_MODELS for model in self.models):
            raise ValueError("models must be a subset of the confirmatory models")
        if not self.candidates:
            raise ValueError("at least one design candidate is required")
        if self.sesoi_d <= 0 or self.main_n < 360:
            raise ValueError("sesoi_d must be positive and main_n at least 360")
        if not 0.0 < self.power_threshold < 1.0 or not 0.0 < self.discrimination_threshold < 1.0:
            raise ValueError("thresholds must be in (0, 1)")
        if self.effect_scale <= 0 or self.min_abs_effect < 0:
            raise ValueError("effect_scale must be positive and min_abs_effect non-negative")


def _paired_power_estimate(
    n_participants: int,
    sesoi_d: float,
    n_simulations: int,
    seed: int,
    within_correlation: float = 0.5,
) -> float:
    """Planning approximation for a paired standardized contrast.

    This is intentionally simple and is used only to reject designs that would fall below the
    power floor. It is not the Stage 0G design-power artifact and does not model the full task.
    """
    rng = np.random.default_rng(seed)
    difference_sd = math.sqrt(max(1e-9, 2.0 * (1.0 - within_correlation)))
    critical = norm.ppf(0.975)
    significant = 0
    for _ in range(n_simulations):
        effects = rng.normal(sesoi_d, difference_sd / math.sqrt(n_participants), size=n_participants)
        observed = float(np.mean(effects))
        standard_error = float(np.std(effects, ddof=1) / math.sqrt(n_participants))
        if standard_error <= 0:
            significant += int(observed > 0)
            continue
        significant += int(observed / standard_error > critical)
    return float(significant / n_simulations)


def _confusion_for_candidate(
    candidate: DesignCandidate,
    config: DesignOptimizationConfig,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, float]]:
    models = tuple(config.models)
    confusion = np.zeros((len(models), len(models)), dtype=int)
    for true_index, true_model in enumerate(models):
        for _ in range(config.n_replicates):
            seed = int(rng.integers(0, 2**31 - 1))
            data, _ = simulate_trial_data(
                model=true_model,
                n_participants=config.n_participants,
                n_trials=config.n_trials,
                seed=seed,
                effect_scale=config.effect_scale,
                min_abs_effect=config.min_abs_effect,
                predict_probability=candidate.predict_probability,
                dual_probability=candidate.dual_probability,
                diagnosticity_range=(candidate.diagnosticity_low, candidate.diagnosticity_high),
                vividness_spread=candidate.vividness_spread,
                confidence_spread=candidate.confidence_spread,
            )
            fits = [
                fit_trial_model(
                    data,
                    model=model,
                    config=TrialModelConfig(
                        n_participants=config.n_participants,
                        n_trials=config.n_trials,
                        n_sbc=1,
                        n_posterior_draws=20,
                        n_recovery=1,
                        seed=seed,
                        max_iter=400,
                        laplace=config.laplace,
                    ),
                )
                for model in models
            ]
            best = int(np.argmin([fit.bic for fit in fits]))
            confusion[true_index, best] += 1
    rows = confusion.sum(axis=1)
    per_model = {
        model: float(confusion[index, index] / max(rows[index], 1))
        for index, model in enumerate(models)
    }
    return confusion, per_model


def _pairwise_accuracy(confusion: np.ndarray, models: tuple[str, ...]) -> dict[str, float]:
    rows = confusion.sum(axis=1)
    pairwise: dict[str, float] = {}
    for left in range(len(models)):
        for right in range(left + 1, len(models)):
            correct = confusion[left, left] + confusion[right, right]
            total = max(rows[left] + rows[right], 1)
            pairwise[f"{models[left]}_vs_{models[right]}"] = float(correct / total)
    return pairwise


def run_design_optimization(
    config: DesignOptimizationConfig | None = None,
    *,
    analysis_prefix: str = "stage0h",
) -> dict[str, Any]:
    cfg = config or DesignOptimizationConfig()
    rng = np.random.default_rng(cfg.seed)
    power = _paired_power_estimate(
        cfg.analysed_n,
        cfg.sesoi_d,
        cfg.n_power_simulations,
        cfg.seed + 7,
    )
    results: list[dict[str, Any]] = []
    for candidate in cfg.candidates:
        confusion, per_model = _confusion_for_candidate(candidate, cfg, rng)
        pairwise = _pairwise_accuracy(confusion, tuple(cfg.models))
        min_pairwise = min(pairwise.values()) if pairwise else 0.0
        overall = float(np.mean(list(per_model.values())))
        results.append(
            {
                "design_id": candidate.design_id,
                "candidate": asdict(candidate),
                "confusion": confusion.tolist(),
                "per_model_accuracy": per_model,
                "pairwise_accuracy": pairwise,
                "overall_balanced_accuracy": overall,
                "min_pairwise_accuracy": float(min_pairwise),
                "power_estimate": power,
            }
        )
    selected = max(
        results,
        key=lambda row: (
            row["min_pairwise_accuracy"],
            row["overall_balanced_accuracy"],
            -abs(row["candidate"]["dual_probability"] - 0.5),
        ),
    )
    passed = (
        selected["min_pairwise_accuracy"] >= cfg.discrimination_threshold
        and power >= cfg.power_threshold
    )
    return {
        "analysis": f"{analysis_prefix}_design_optimization",
        "scope": SCOPE,
        "models": list(cfg.models),
        "config": asdict(cfg),
        "power": {
            "estimate": power,
            "threshold": cfg.power_threshold,
            "method": "paired_normal_approximation_not_stage0g_power",
            "analysed_n": cfg.analysed_n,
            "sesoi_d": cfg.sesoi_d,
        },
        "results": results,
        "selected_design": selected,
        "decision": (
            f"CRT_{analysis_prefix.upper()}_DESIGN_OPTIMIZATION_PASS"
            if passed
            else f"CRT_{analysis_prefix.upper()}_DESIGN_OPTIMIZATION_REVIEW"
        ),
        "note": (
            "Offline simulation screening only. The selected trial composition must be frozen before "
            "registration; the classifier used to rank candidates is not a hypothesis test."
        ),
    }


@dataclass(frozen=True)
class HierarchicalDesignConfig:
    """Target-scale design screen using the full joint model, not the readout surrogate."""

    n_participants: int = 12
    n_trials: int = 40
    n_replicates: int = 2
    models: tuple[str, ...] = FULL_MODELS
    candidates: tuple[DesignCandidate, ...] = DEFAULT_CANDIDATES
    recovery_threshold: float = 0.85
    effect_scale: float = 0.8
    min_abs_effect: float = 0.25
    max_iter: int = 200
    seed: int = 20261031

    def __post_init__(self) -> None:
        if self.n_participants < 6 or self.n_trials < 20:
            raise ValueError("hierarchical design screen requires at least 6 participants and 20 trials")
        if self.n_replicates <= 0:
            raise ValueError("n_replicates must be positive")
        if not self.models or any(model not in FULL_MODELS for model in self.models):
            raise ValueError("models must be a non-empty subset of FULL_MODELS")
        if not self.candidates:
            raise ValueError("at least one design candidate is required")
        if not 0 < self.recovery_threshold <= 1:
            raise ValueError("recovery_threshold must be in (0, 1]")


def run_hierarchical_design_optimization(
    config: HierarchicalDesignConfig | None = None,
) -> dict[str, Any]:
    """Evaluate candidates with the full joint model and BIC selection.

    This is still a simulation screen, but it removes the readout/full-model mismatch in the Stage 0H
    optimizer. A PASS requires the minimum pairwise balanced accuracy to clear the threshold; it is
    not human evidence and not a substitute for the target-scale SBC/recovery artifacts.
    """
    cfg = config or HierarchicalDesignConfig()
    rng = np.random.default_rng(cfg.seed)
    results: list[dict[str, Any]] = []
    for candidate in cfg.candidates:
        confusion = np.zeros((len(cfg.models), len(cfg.models)), dtype=int)
        for true_index, true_model in enumerate(cfg.models):
            for _ in range(cfg.n_replicates):
                seed = int(rng.integers(0, 2**31 - 1))
                data, _ = simulate_full_data(
                    true_model,
                    n_participants=cfg.n_participants,
                    n_trials=cfg.n_trials,
                    seed=seed,
                    effect_scale=cfg.effect_scale,
                    min_abs_effect=cfg.min_abs_effect,
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
                            n_participants=cfg.n_participants,
                            n_trials=cfg.n_trials,
                            n_sbc=1,
                            n_posterior_draws=20,
                            n_recovery=1,
                            seed=seed,
                            max_iter=cfg.max_iter,
                        ),
                    )
                    for model in cfg.models
                ]
                confusion[true_index, int(np.argmin([fit.bic for fit in fits]))] += 1
        rows = confusion.sum(axis=1)
        per_model = {
            model: float(confusion[index, index] / max(rows[index], 1))
            for index, model in enumerate(cfg.models)
        }
        pairwise = _pairwise_accuracy(confusion, tuple(cfg.models))
        minimum = min(pairwise.values()) if pairwise else 0.0
        results.append(
            {
                "design_id": candidate.design_id,
                "candidate": asdict(candidate),
                "confusion": confusion.tolist(),
                "per_model_accuracy": per_model,
                "pairwise_accuracy": pairwise,
                "overall_balanced_accuracy": float(np.mean(list(per_model.values()))),
                "min_pairwise_accuracy": float(minimum),
            }
        )
    selected = max(
        results,
        key=lambda row: (row["min_pairwise_accuracy"], row["overall_balanced_accuracy"]),
    )
    complete_model_set = set(cfg.models) == set(FULL_MODELS)
    passed = selected["min_pairwise_accuracy"] >= cfg.recovery_threshold and complete_model_set
    return {
        "analysis": "stage0i_hierarchical_design",
        "scope": "offline_full_model_design_screening_not_human_evidence",
        "method": "full_joint_model_bic_screen",
        "models": list(cfg.models),
        "config": asdict(cfg),
        "results": results,
        "selected_design": selected,
        "decision": (
            "CRT_STAGE0I_DESIGN_ADO_PASS"
            if passed
            else "CRT_STAGE0I_DESIGN_ADO_REVIEW"
        ),
        "note": (
            "Target-scale screening with the full joint likelihood. A PASS requires all confirmatory "
            "models and is design evidence only; the final candidate still requires SBC, recovery, "
            "calibration, and independent review."
        ),
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def write_artifact(payload: Mapping[str, Any], path) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run a small screening pass")
    parser.add_argument("--write", action="store_true", help="write the Stage 0H design artifact")
    parser.add_argument("--out", type=Path, default=Path("results/crt/CRT_STAGE0H_DESIGN_OPTIMIZATION.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.check and not args.write:
        parser.print_help()
        return 0
    cfg = DesignOptimizationConfig(
        n_participants=12,
        n_trials=40,
        n_replicates=1,
        n_power_simulations=40,
        candidates=DEFAULT_CANDIDATES[:2],
    )
    payload = run_design_optimization(cfg)
    if args.write:
        write_artifact(payload, args.out)
    print(json.dumps({"decision": payload["decision"], "selected": payload["selected_design"]["design_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

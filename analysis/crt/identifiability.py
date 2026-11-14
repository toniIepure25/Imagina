"""Pairwise identifiability checks for the CRT confirmatory model space.

The module is deliberately simulation-only. It asks whether the full joint model can recover the
generating model at a declared sample size and trial count; it does not analyse human data and does
not establish that any model is true.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .full_model import FULL_MODELS, FullModelConfig, fit_full_model, simulate_full_data

SCOPE = "offline_pairwise_identifiability_simulation_not_human_evidence"
CONFIRMATORY = {"M0", "M2", "M4", "M6", "M7"}


@dataclass(frozen=True)
class IdentifiabilityConfig:
    n_participants: int = 12
    n_trials: int = 40
    n_simulations: int = 3
    n_posterior_draws: int = 20
    max_iter: int = 200
    models: tuple[str, ...] = FULL_MODELS
    recovery_threshold: float = 0.85
    lower_bound_threshold: float = 0.80
    effect_scale: float = 0.8
    min_abs_effect: float = 0.25
    seed: int = 20261031

    def __post_init__(self) -> None:
        if self.n_participants < 6 or self.n_trials < 20:
            raise ValueError("identifiability simulation requires at least 6 participants and 20 trials")
        if self.n_simulations <= 0 or self.n_posterior_draws < 20:
            raise ValueError("simulation and posterior-draw counts must be positive")
        if not self.models or any(model not in FULL_MODELS for model in self.models):
            raise ValueError("models must be a non-empty subset of FULL_MODELS")
        if not 0 < self.recovery_threshold <= 1 or not 0 < self.lower_bound_threshold <= 1:
            raise ValueError("recovery thresholds must be in (0, 1]")


def _wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return float(max(0.0, (centre - spread) / denominator))


def _pairwise(
    confusion: np.ndarray, models: tuple[str, ...]
) -> dict[str, dict[str, float]]:
    rows = confusion.sum(axis=1)
    result: dict[str, dict[str, float]] = {}
    for left in range(len(models)):
        for right in range(left + 1, len(models)):
            successes = int(confusion[left, left] + confusion[right, right])
            total = int(rows[left] + rows[right])
            result[f"{models[left]}_vs_{models[right]}"] = {
                "accuracy": float(successes / max(total, 1)),
                "lower_bound": _wilson_lower(successes, total),
                "n": total,
            }
    return result


def _fit_condition(fits: list[Any]) -> float:
    conditions: list[float] = []
    for fit in fits:
        draws = np.asarray(fit.posterior_draws, dtype=float)
        if draws.ndim != 2 or draws.shape[0] < 2:
            continue
        covariance = np.cov(draws, rowvar=False)
        eigenvalues = np.linalg.eigvalsh((covariance + covariance.T) / 2.0)
        positive = eigenvalues[eigenvalues > 1e-12]
        if positive.size:
            conditions.append(float(positive.max() / positive.min()))
    return float(max(conditions)) if conditions else float("nan")


def run_identifiability(config: IdentifiabilityConfig | None = None) -> dict[str, Any]:
    cfg = config or IdentifiabilityConfig()
    rng = np.random.default_rng(cfg.seed)
    models = tuple(cfg.models)
    confusion = np.zeros((len(models), len(models)), dtype=int)
    evidence_sums = np.zeros((len(models), len(models)), dtype=float)
    conditions: list[float] = []

    for true_index, true_model in enumerate(models):
        for _ in range(cfg.n_simulations):
            seed = int(rng.integers(0, 2**31 - 1))
            data, _ = simulate_full_data(
                true_model,
                n_participants=cfg.n_participants,
                n_trials=cfg.n_trials,
                seed=seed,
                effect_scale=cfg.effect_scale,
                min_abs_effect=cfg.min_abs_effect,
            )
            fits = [
                fit_full_model(
                    data,
                    model,
                    FullModelConfig(
                        n_participants=cfg.n_participants,
                        n_trials=cfg.n_trials,
                        n_sbc=1,
                        n_posterior_draws=cfg.n_posterior_draws,
                        n_recovery=1,
                        seed=seed,
                        max_iter=cfg.max_iter,
                    ),
                )
                for model in models
            ]
            best = int(np.argmin([fit.bic for fit in fits]))
            confusion[true_index, best] += 1
            for other_index, fit in enumerate(fits):
                evidence_sums[true_index, other_index] += (fit.bic - fits[true_index].bic) / 2.0
            conditions.append(_fit_condition(fits))

    rows = confusion.sum(axis=1)
    per_model = {
        model: {
            "accuracy": float(confusion[index, index] / max(rows[index], 1)),
            "lower_bound": _wilson_lower(int(confusion[index, index]), int(rows[index])),
        }
        for index, model in enumerate(models)
    }
    pairwise = _pairwise(confusion, models)
    min_pairwise = min(row["accuracy"] for row in pairwise.values()) if pairwise else 0.0
    min_lower = min(row["lower_bound"] for row in pairwise.values()) if pairwise else 0.0
    min_per_model = min(row["accuracy"] for row in per_model.values()) if per_model else 0.0
    complete_model_set = set(models) == CONFIRMATORY
    passed = (
        complete_model_set
        and min_pairwise >= cfg.recovery_threshold
        and min_lower >= cfg.lower_bound_threshold
        and min_per_model >= cfg.lower_bound_threshold
    )
    evidence = {
        f"{models[i]}_vs_{models[j]}": {
            "mean_expected_log_evidence_difference": float(
                evidence_sums[i, j] / max(cfg.n_simulations, 1)
            )
        }
        for i in range(len(models))
        for j in range(i + 1, len(models))
    }
    return {
        "analysis": "stage0i_identifiability",
        "scope": SCOPE,
        "models": list(models),
        "config": asdict(cfg),
        "confusion": confusion.tolist(),
        "per_model": per_model,
        "pairwise": pairwise,
        "evidence": evidence,
        "fisher_condition_max": float(np.nanmax(conditions)) if conditions else None,
        "minimum_pairwise_accuracy": float(min_pairwise),
        "minimum_pairwise_lower_bound": float(min_lower),
        "minimum_per_model_accuracy": float(min_per_model),
        "decision": (
            "CRT_STAGE0I_IDENTIFIABILITY_PASS"
            if passed
            else "CRT_STAGE0I_IDENTIFIABILITY_REVIEW"
        ),
        "note": (
            "Simulation-only pairwise model recovery. A REVIEW means the declared design does not "
            "separate the confirmatory models with the required uncertainty margin; it is not human evidence."
        ),
    }


def write_artifact(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("results/crt/CRT_STAGE0I_IDENTIFIABILITY.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    cfg = IdentifiabilityConfig(n_participants=6, n_trials=20, n_simulations=1, n_posterior_draws=20)
    payload = run_identifiability(cfg)
    if args.write:
        write_artifact(payload, args.out)
    print(json.dumps({"decision": payload["decision"], "min_pairwise": payload["minimum_pairwise_accuracy"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic offline simulation for the ANIMUS reconstruction instrument.

This harness checks policy mechanics and parameter recovery under a known synthetic model. It is not
participant evidence, not a validation of the reconstruction tasks, and not a training-outcome study.
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any

from app.core.animus.studio.adaptive import (
    SELECTABLE_DIMENSIONS,
    select_action,
    update_difficulty,
)
from app.core.animus.studio.profile import (
    apply_observation,
    calibration_from_stats,
    estimate_from_stats,
)

DEFAULT_LATENT = {
    "stability": 0.72,
    "discrimination": 0.58,
    "spatial": 0.66,
    "control": 0.61,
}
POLICIES = ("coverage_first", "information_gain", "fixed_cycle")


def _coverage_choice(stats: dict[str, dict[str, Any]]) -> str:
    return min(SELECTABLE_DIMENSIONS,
               key=lambda name: (int(estimate_from_stats(stats.get(name)).get("n") or 0),
                                 SELECTABLE_DIMENSIONS.index(name)))


def _choose(policy: str, stats: dict[str, dict[str, Any]], trial_index: int,
            seed: int, difficulty: float) -> tuple[str, str]:
    if policy == "coverage_first":
        return _coverage_choice(stats), "coverage_floor"
    if policy == "fixed_cycle":
        return SELECTABLE_DIMENSIONS[trial_index % len(SELECTABLE_DIMENSIONS)], "fixed_cycle"
    action = select_action(stats, trial_index=trial_index, seed=seed, difficulty=difficulty)
    return action["dimension"], action["reason"]


def simulate(policy: str = "information_gain", *, latent: dict[str, float] | None = None,
             trials: int = 60, seed: int = 7, confidence: float = 0.7) -> dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    if trials < 4:
        raise ValueError("trials must be at least 4")
    truth = {name: float(value) for name, value in (latent or DEFAULT_LATENT).items()}
    if set(truth) != set(SELECTABLE_DIMENSIONS):
        raise ValueError("latent must define every selectable dimension")
    if any(not 0.0 < value < 1.0 for value in truth.values()):
        raise ValueError("latent probabilities must be between 0 and 1")

    rng = random.Random(f"{seed}:{policy}")
    stats: dict[str, dict[str, Any]] = {}
    calibration = None
    recent_scores: list[float] = []
    difficulty = 0.45
    counts = {name: 0 for name in SELECTABLE_DIMENSIONS}
    reasons: dict[str, int] = {}

    for trial_index in range(trials):
        dimension, reason = _choose(policy, stats, trial_index, seed, difficulty)
        reasons[reason] = reasons.get(reason, 0) + 1
        score = 1.0 if rng.random() < truth[dimension] else 0.0
        stats[dimension] = apply_observation(stats.get(dimension), score=score, confidence=confidence)
        calibration = apply_observation(calibration, score=score, confidence=confidence)
        counts[dimension] += 1
        recent_scores.append(score)
        difficulty = update_difficulty(difficulty, recent_scores)

    estimates = {name: estimate_from_stats(stats.get(name)) for name in SELECTABLE_DIMENSIONS}
    errors = [float(estimates[name]["estimate"]) - truth[name]
              for name in SELECTABLE_DIMENSIONS if estimates[name]["estimate"] is not None]
    covered = sum(1 for name in SELECTABLE_DIMENSIONS
                  if int(estimates[name]["n"]) >= 3)
    uncertainty = [float(estimates[name]["uncertainty"])
                   for name in SELECTABLE_DIMENSIONS if estimates[name]["n"]]
    calibration_summary = calibration_from_stats(calibration)

    return {
        "policy": policy,
        "seed": seed,
        "trials": trials,
        "latent": truth,
        "counts": counts,
        "reasons": reasons,
        "estimates": {
            name: {
                "estimate": estimates[name]["estimate"],
                "uncertainty": estimates[name]["uncertainty"],
                "n": estimates[name]["n"],
            }
            for name in SELECTABLE_DIMENSIONS
        },
        "metrics": {
            "rmse": round((sum(error * error for error in errors) / len(errors)) ** 0.5, 6)
            if errors else None,
            "coverage": round(covered / len(SELECTABLE_DIMENSIONS), 4),
            "mean_uncertainty": round(sum(uncertainty) / len(uncertainty), 6) if uncertainty else None,
            "brier": calibration_summary["brier_score"],
        },
        "disclaimer": "Synthetic policy check only; not human validation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=POLICIES, default="information_gain")
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(json.dumps(simulate(args.policy, trials=args.trials, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()

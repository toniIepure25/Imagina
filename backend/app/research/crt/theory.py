"""Competing-model signatures for the CRT Stage 0D theory tournament.

This is a design-identifiability analysis, not a fit to human data. Each model
predicts a five-dimensional signature before the confirmatory study. The module
asks whether the signatures are separable under measurement noise. If they are
not, the planned experiment cannot distinguish the theories and should not be
run as a decisive test.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Mapping, Sequence

MODELS: tuple[str, ...] = (
    "crt_meta_eig",
    "eig_only",
    "higher_order_precision",
    "sdt_confidence",
    "heuristic_source",
)

SIGNATURE_NAMES: tuple[str, ...] = (
    "prediction_advantage",
    "meta_eig_efficiency",
    "active_selection_gain",
    "specificity_gain",
    "prediction_error_update",
)

THEORY_SIGNATURES: dict[str, tuple[float, ...]] = {
    "crt_meta_eig": (0.12, 0.55, 0.03, 0.08, 0.15),
    "eig_only": (0.00, 0.08, 0.03, 0.00, 0.00),
    "higher_order_precision": (0.00, 0.30, 0.01, 0.00, 0.00),
    "sdt_confidence": (0.00, 0.00, 0.00, 0.00, 0.00),
    "heuristic_source": (0.00, -0.05, -0.02, 0.00, 0.00),
}


@dataclass(frozen=True)
class TheoryConfig:
    n_observations: int = 40
    noise_sd: float = 0.03
    seed: int = 20261029
    recovery_threshold: float = 0.80

    def __post_init__(self) -> None:
        if self.n_observations <= 0:
            raise ValueError("n_observations must be positive")
        if self.noise_sd < 0:
            raise ValueError("noise_sd must be non-negative")
        if not 0.0 < self.recovery_threshold <= 1.0:
            raise ValueError("recovery_threshold must be in (0, 1]")


def signature_vector(model: str) -> tuple[float, ...]:
    if model not in THEORY_SIGNATURES:
        raise ValueError(f"unknown theory model: {model}")
    return THEORY_SIGNATURES[model]


def signature_distance(observed: Sequence[float], model: str) -> float:
    expected = signature_vector(model)
    if len(observed) != len(expected):
        raise ValueError("observed signature has the wrong length")
    return math.sqrt(sum((float(value) - target) ** 2 for value, target in zip(observed, expected)))


def classify_signature(observed: Sequence[float]) -> str:
    if len(observed) != len(SIGNATURE_NAMES):
        raise ValueError("observed signature has the wrong length")
    return min(MODELS, key=lambda model: signature_distance(observed, model))


def simulate_signature(model: str, config: TheoryConfig, rng: random.Random) -> tuple[float, ...]:
    base = signature_vector(model)
    return tuple(value + rng.gauss(0.0, config.noise_sd) for value in base)


def run_theory_tournament(config: TheoryConfig | None = None) -> dict[str, object]:
    config = config or TheoryConfig()
    rng = random.Random(config.seed)
    confusion = {model: {candidate: 0 for candidate in MODELS} for model in MODELS}
    for true_model in MODELS:
        for _ in range(config.n_observations):
            observed = simulate_signature(true_model, config, rng)
            predicted = classify_signature(observed)
            confusion[true_model][predicted] += 1
    diagonal = {model: confusion[model][model] / config.n_observations for model in MODELS}
    balanced_accuracy = mean(diagonal.values())
    passed = balanced_accuracy >= config.recovery_threshold
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0d_model_signature_separability",
        "config": {
            "n_observations": config.n_observations,
            "noise_sd": config.noise_sd,
            "seed": config.seed,
            "recovery_threshold": config.recovery_threshold,
        },
        "signature_names": list(SIGNATURE_NAMES),
        "signatures": {model: list(THEORY_SIGNATURES[model]) for model in MODELS},
        "confusion": confusion,
        "diagonal": {model: round(value, 6) for model, value in diagonal.items()},
        "balanced_accuracy": round(balanced_accuracy, 6),
        "decision": "CRT_STAGE0D_THEORY_PASS" if passed else "CRT_STAGE0D_THEORY_REVIEW",
        "note": (
            "Design-signature separability only. It does not estimate human model evidence. "
            "A REVIEW means the planned contrasts cannot distinguish the theories under the stated noise."
        ),
    }


def check_theory() -> dict[str, object]:
    report = run_theory_tournament(TheoryConfig(n_observations=20, noise_sd=0.02, seed=7))
    if report["decision"] != "CRT_STAGE0D_THEORY_PASS":
        raise AssertionError(f"CRT theory tournament failed: {report['confusion']}")
    return report


def model_predictions() -> Mapping[str, Mapping[str, float]]:
    return {
        model: dict(zip(SIGNATURE_NAMES, values))
        for model, values in THEORY_SIGNATURES.items()
    }


__all__ = [
    "MODELS",
    "SIGNATURE_NAMES",
    "THEORY_SIGNATURES",
    "TheoryConfig",
    "check_theory",
    "classify_signature",
    "model_predictions",
    "run_theory_tournament",
    "signature_distance",
    "signature_vector",
    "simulate_signature",
]

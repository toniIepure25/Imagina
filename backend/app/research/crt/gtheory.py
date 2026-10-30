"""Generalizability-theory helpers for the CRT measurement plan.

The module is simulation-only. It estimates variance components for a
participants x occasions design and reports a decision study for the number of
occasions. It does not fit human data and does not authorize a measurement
claim.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Sequence

_EPS = 1e-12


@dataclass(frozen=True)
class VarianceComponents:
    person: float
    occasion: float
    error: float
    total: float
    negative: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "person": round(self.person, 6),
            "occasion": round(self.occasion, 6),
            "error": round(self.error, 6),
            "total": round(self.total, 6),
            "negative": list(self.negative),
        }


@dataclass(frozen=True)
class GTheoryConfig:
    n_participants: int = 60
    n_occasions: int = 2
    person_sd: float = 1.0
    occasion_sd: float = 0.2
    error_sd: float = 0.5
    seed: int = 20261029
    min_relative_reliability: float = 0.70

    def __post_init__(self) -> None:
        if self.n_participants < 4:
            raise ValueError("n_participants must be at least 4")
        if self.n_occasions < 2:
            raise ValueError("n_occasions must be at least 2")
        if self.person_sd < 0 or self.occasion_sd < 0 or self.error_sd < 0:
            raise ValueError("variance sources must be non-negative")
        if not 0.0 < self.min_relative_reliability < 1.0:
            raise ValueError("min_relative_reliability must be between 0 and 1")


def two_way_variance_components(matrix: Sequence[Sequence[float]]) -> VarianceComponents:
    """Return ANOVA variance components for a fully crossed persons x occasions design."""
    if len(matrix) < 2:
        raise ValueError("at least two participants are required")
    k = len(matrix[0])
    if k < 2:
        raise ValueError("at least two occasions are required")
    if any(len(row) != k for row in matrix):
        raise ValueError("all participant rows must have the same number of occasions")
    n = len(matrix)
    grand = mean(value for row in matrix for value in row)
    person_means = [mean(row) for row in matrix]
    occasion_means = [mean(row[index] for row in matrix) for index in range(k)]
    ss_person = k * sum((value - grand) ** 2 for value in person_means)
    ss_occasion = n * sum((value - grand) ** 2 for value in occasion_means)
    ss_total = sum((value - grand) ** 2 for row in matrix for value in row)
    ss_error = max(0.0, ss_total - ss_person - ss_occasion)
    ms_person = ss_person / (n - 1)
    ms_occasion = ss_occasion / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))
    person = max(0.0, (ms_person - ms_error) / k)
    occasion = max(0.0, (ms_occasion - ms_error) / n)
    error = max(0.0, ms_error)
    total = person + occasion + error
    negative: list[str] = []
    if ms_person < ms_error:
        negative.append("person")
    if ms_occasion < ms_error:
        negative.append("occasion")
    return VarianceComponents(person, occasion, error, total, tuple(negative))


def d_study(components: VarianceComponents, n_occasions: int) -> dict[str, float]:
    if n_occasions <= 0:
        raise ValueError("n_occasions must be positive")
    denominator = components.person + components.error / n_occasions
    relative = components.person / denominator if denominator > _EPS else 0.0
    absolute_denominator = (
        components.person + components.occasion / n_occasions + components.error / n_occasions
    )
    absolute = components.person / absolute_denominator if absolute_denominator > _EPS else 0.0
    sem_relative = math.sqrt(max(0.0, components.error / n_occasions))
    sem_absolute = math.sqrt(max(0.0, (components.occasion + components.error) / n_occasions))
    return {
        "n_occasions": float(n_occasions),
        "relative_reliability": round(relative, 6),
        "absolute_reliability": round(absolute, 6),
        "sem": round(sem_relative, 6),
        "sem_relative": round(sem_relative, 6),
        "sem_absolute": round(sem_absolute, 6),
        "mdc95": round(1.959963984540054 * math.sqrt(2.0) * sem_relative, 6),
        "mdc95_absolute": round(1.959963984540054 * math.sqrt(2.0) * sem_absolute, 6),
    }


def simulate_matrix(config: GTheoryConfig) -> list[list[float]]:
    rng = random.Random(config.seed)
    occasion_effect = [rng.gauss(0.0, config.occasion_sd) for _ in range(config.n_occasions)]
    rows: list[list[float]] = []
    for _ in range(config.n_participants):
        person_effect = rng.gauss(0.0, config.person_sd)
        rows.append(
            [
                person_effect
                + occasion_effect[index]
                + rng.gauss(0.0, config.error_sd)
                for index in range(config.n_occasions)
            ]
        )
    return rows


def run_gtheory(config: GTheoryConfig | None = None) -> dict[str, object]:
    config = config or GTheoryConfig()
    matrix = simulate_matrix(config)
    components = two_way_variance_components(matrix)
    study = [d_study(components, occasions) for occasions in (1, 2, 3, 4)]
    target = next(row for row in study if row["n_occasions"] == float(config.n_occasions))
    passed = target["relative_reliability"] >= config.min_relative_reliability
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0d_generalizability_theory_decision_study",
        "config": {
            "n_participants": config.n_participants,
            "n_occasions": config.n_occasions,
            "person_sd": config.person_sd,
            "occasion_sd": config.occasion_sd,
            "error_sd": config.error_sd,
            "seed": config.seed,
            "min_relative_reliability": config.min_relative_reliability,
        },
        "variance_components": components.as_dict(),
        "d_study": study,
        "decision": "CRT_STAGE0D_GTHEORY_PASS" if passed else "CRT_STAGE0D_GTHEORY_REVIEW",
        "note": (
            "Simulation-only variance-component recovery and decision study. "
            "It does not estimate reliability from human data or authorize an individual-level claim."
        ),
    }


def check_gtheory() -> dict[str, object]:
    report = run_gtheory(GTheoryConfig(n_participants=30, n_occasions=2, seed=7))
    if report["decision"] != "CRT_STAGE0D_GTHEORY_PASS":
        raise AssertionError(f"CRT G-theory gate failed: {report['variance_components']}")
    return report


__all__ = [
    "GTheoryConfig",
    "VarianceComponents",
    "check_gtheory",
    "d_study",
    "run_gtheory",
    "simulate_matrix",
    "two_way_variance_components",
]

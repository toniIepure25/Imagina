"""Stage 0E test-facet reliability simulation for CRT."""
from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean

from app.research.crt.gtheory import d_study, two_way_variance_components
from app.research.crt.model import TEST_IDS


@dataclass(frozen=True)
class PsychometricConfig:
    n_participants: int = 60
    n_tests: int = len(TEST_IDS)
    n_occasions: int = 2
    person_sd: float = 1.0
    test_sd: float = 0.25
    occasion_sd: float = 0.2
    error_sd: float = 0.5
    seed: int = 20261030
    min_reliability: float = 0.70

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_tests <= 0:
            raise ValueError("n_tests must be positive")
        if self.n_occasions < 2:
            raise ValueError("n_occasions must be at least two")


def simulate_facet_matrices(
    config: PsychometricConfig | None = None,
) -> list[list[list[float]]]:
    """Return one persons x occasions matrix per test, with shared person and test effects."""

    config = config or PsychometricConfig()
    rng = random.Random(config.seed)
    person_effects = [rng.gauss(0.0, config.person_sd) for _ in range(config.n_participants)]
    test_effects = [rng.gauss(0.0, config.test_sd) for _ in range(config.n_tests)]
    matrices: list[list[list[float]]] = []
    for test in range(config.n_tests):
        matrix: list[list[float]] = []
        for person in range(config.n_participants):
            row = []
            for occasion in range(config.n_occasions):
                value = (
                    person_effects[person]
                    + test_effects[test]
                    + rng.gauss(0.0, config.occasion_sd)
                    + rng.gauss(0.0, config.error_sd)
                )
                row.append(value)
            matrix.append(row)
        matrices.append(matrix)
    return matrices


def compute_test_facet_reliability(matrices: list[list[list[float]]]) -> list[float]:
    reliabilities: list[float] = []
    for matrix in matrices:
        components = two_way_variance_components(matrix)
        reliabilities.append(float(d_study(components, len(matrix[0]))["relative_reliability"]))
    return reliabilities


def run_psychometrics(config: PsychometricConfig | None = None) -> dict[str, object]:
    config = config or PsychometricConfig()
    matrices = simulate_facet_matrices(config)
    reliabilities = compute_test_facet_reliability(matrices)
    minimum = min(reliabilities) if reliabilities else 0.0
    average = mean(reliabilities) if reliabilities else 0.0
    passed = minimum >= config.min_reliability
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_test_facet_reliability",
        "config": {
            "n_participants": config.n_participants,
            "n_tests": config.n_tests,
            "n_occasions": config.n_occasions,
            "seed": config.seed,
            "min_reliability": config.min_reliability,
        },
        "test_reliability": {
            TEST_IDS[index] if index < len(TEST_IDS) else f"test-{index}": round(value, 6)
            for index, value in enumerate(reliabilities)
        },
        "summary": {
            "minimum": round(minimum, 6),
            "mean": round(average, 6),
        },
        "decision": "CRT_STAGE0E_PSYCHOMETRIC_PASS"
        if passed
        else "CRT_STAGE0E_PSYCHOMETRIC_REVIEW",
        "note": (
            "Simulated test-facet reliability, not human evidence. The model includes a shared person "
            "effect and a shared test effect; the D-study uses two occasions. A REVIEW means the current "
            "test menu does not clear the pre-specified facet floor."
        ),
    }


__all__ = [
    "PsychometricConfig",
    "compute_test_facet_reliability",
    "run_psychometrics",
    "simulate_facet_matrices",
]

"""Design helpers for the Stage 0 Counterfactual Reality Testing simulator."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence

import numpy as np

from app.research.crt.model import (
    ALL_TESTS,
    DEFAULT_PRIOR,
    SOURCES,
    TEST_AGENCY,
    TEST_COMPLEXITY,
    TEST_COSTS,
    TEST_IDS,
)
from app.research.prm.power import approximate_lower_bound, icc_2_1


@dataclass(frozen=True)
class TestSpec:
    test: int
    name: str
    cost: float
    complexity: float
    agency_value: float


@dataclass(frozen=True)
class BlockSpec:
    name: str
    n_trials: int
    condition: str
    cost_multiplier: float = 1.0
    source_prior: tuple[float, float, float, float] = DEFAULT_PRIOR


DEFAULT_TESTS: tuple[TestSpec, ...] = tuple(
    TestSpec(
        test=index,
        name=TEST_IDS[index],
        cost=TEST_COSTS[index],
        complexity=TEST_COMPLEXITY[index],
        agency_value=TEST_AGENCY[index],
    )
    for index in ALL_TESTS
)

CONDITIONS: tuple[str, ...] = (
    "observe",
    "active_intervene",
    "active_predict",
    "yoked_intervene",
    "yoked_predict",
)


def test_costs(tests: Sequence[TestSpec] = DEFAULT_TESTS, multiplier: float = 1.0) -> tuple[float, ...]:
    if multiplier < 0:
        raise ValueError("cost multiplier must be non-negative")
    return tuple(test.cost * multiplier for test in tests)


def test_complexities(tests: Sequence[TestSpec] = DEFAULT_TESTS) -> tuple[float, ...]:
    return tuple(test.complexity for test in tests)


def test_agency_values(tests: Sequence[TestSpec] = DEFAULT_TESTS) -> tuple[float, ...]:
    return tuple(test.agency_value for test in tests)


def source_schedule(
    n_trials: int,
    seed: int,
    prior: Sequence[float] = DEFAULT_PRIOR,
) -> list[int]:
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    if len(prior) != len(SOURCES):
        raise ValueError("prior must have one probability per source")
    rng = random.Random(seed)
    if all(abs(value - 0.25) < 1e-12 for value in prior):
        schedule = [index % len(SOURCES) for index in range(n_trials)]
    else:
        total = sum(prior)
        if total <= 0:
            raise ValueError("prior must have positive mass")
        probabilities = [value / total for value in prior]
        schedule = rng.choices(range(len(SOURCES)), weights=probabilities, k=n_trials)
    rng.shuffle(schedule)
    return schedule


def default_blocks() -> tuple[BlockSpec, ...]:
    return (
        BlockSpec("observe", 20, "observe"),
        BlockSpec("active_intervene", 30, "active_intervene"),
        BlockSpec("active_predict", 30, "active_predict"),
        BlockSpec("yoked_intervene", 30, "yoked_intervene"),
        BlockSpec("yoked_predict", 30, "yoked_predict"),
    )


def yoked_test_sequence(tests: Sequence[tuple[int, bool]]) -> tuple[int, ...]:
    return tuple(test for test, _ in tests)


@dataclass(frozen=True)
class DesignPowerConfig:
    n_participants: int = 240
    trials_per_cell_per_occasion: int = 25
    occasions: int = 2
    n_simulations: int = 400
    seed: int = 20261030
    alpha: float = 0.05
    sesoi_d: float = 0.20
    baseline_accuracy: float = 0.50
    between_sd: float = 0.12
    within_correlation: float = 0.50
    attrition: float = 0.10
    false_seen_baseline: float = 0.20
    false_seen_effect: float = 0.05
    false_seen_sd: float = 0.12
    false_seen_trials_per_arm: int = 40

    def __post_init__(self) -> None:
        if self.n_participants < 4:
            raise ValueError("n_participants must be at least 4")
        if self.trials_per_cell_per_occasion <= 0:
            raise ValueError("trials_per_cell_per_occasion must be positive")
        if self.occasions <= 0:
            raise ValueError("occasions must be positive")
        if self.n_simulations <= 0:
            raise ValueError("n_simulations must be positive")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1")
        if self.sesoi_d <= 0:
            raise ValueError("sesoi_d must be positive")
        if not 0.0 < self.baseline_accuracy < 1.0:
            raise ValueError("baseline_accuracy must be between 0 and 1")
        if self.between_sd <= 0:
            raise ValueError("between_sd must be positive")
        if not -0.99 < self.within_correlation < 0.99:
            raise ValueError("within_correlation must be between -0.99 and 0.99")
        if not 0.0 <= self.attrition < 1.0:
            raise ValueError("attrition must be in [0, 1)")
        if not 0.0 < self.false_seen_baseline < 1.0:
            raise ValueError("false_seen_baseline must be between 0 and 1")
        if self.false_seen_effect <= 0:
            raise ValueError("false_seen_effect must be positive")
        if self.false_seen_sd <= 0:
            raise ValueError("false_seen_sd must be positive")


def _paired_power_from_rates(
    *,
    n_participants: int,
    trials_per_condition: int,
    baseline: float,
    effect: float,
    between_sd: float,
    within_correlation: float,
    n_simulations: int,
    alpha: float,
    seed: int,
) -> tuple[float, float]:
    """Power for a paired binomial contrast.

    This is a planning approximation, not the CRT generative model: it captures between-person
    heterogeneity, within-person correlation, and trial-level binomial noise.
    """
    if trials_per_condition <= 0:
        raise ValueError("trials_per_condition must be positive")
    if n_participants < 4:
        raise ValueError("n_participants must be at least 4")
    rng = np.random.default_rng(seed)
    base_latent = rng.normal(0.0, between_sd, size=(n_simulations, n_participants))
    shared = rng.normal(0.0, 1.0, size=(n_simulations, n_participants))
    noise = math.sqrt(max(0.0, 1.0 - within_correlation**2)) * rng.normal(
        0.0, 1.0, size=(n_simulations, n_participants)
    )
    condition_shift = effect + between_sd * (within_correlation * shared + noise - shared)
    p1 = np.clip(baseline + base_latent, 0.02, 0.98)
    p2 = np.clip(baseline + base_latent + condition_shift, 0.02, 0.98)
    x1 = rng.binomial(trials_per_condition, p1)
    x2 = rng.binomial(trials_per_condition, p2)
    differences = (x2 - x1) / trials_per_condition
    means = differences.mean(axis=1)
    spreads = differences.std(axis=1, ddof=1)
    standard_errors = spreads / math.sqrt(n_participants)
    t_values = np.divide(
        means,
        standard_errors,
        out=np.zeros_like(means),
        where=standard_errors > 0,
    )
    critical = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    power = float(np.mean(np.abs(t_values) >= critical))
    return power, float(means.mean())


def simulate_design_power(config: DesignPowerConfig | None = None) -> dict[str, object]:
    config = config or DesignPowerConfig()
    rng = random.Random(config.seed)
    effective_n = max(4, int(round(config.n_participants * (1.0 - config.attrition))))
    trials_per_condition = config.trials_per_cell_per_occasion * config.occasions
    power, mean_effect = _paired_power_from_rates(
        n_participants=effective_n,
        trials_per_condition=trials_per_condition,
        baseline=config.baseline_accuracy,
        effect=config.sesoi_d * config.between_sd,
        between_sd=config.between_sd,
        within_correlation=config.within_correlation,
        n_simulations=config.n_simulations,
        alpha=config.alpha,
        seed=config.seed,
    )
    false_seen_power, false_seen_mean = _paired_power_from_rates(
        n_participants=effective_n,
        trials_per_condition=config.false_seen_trials_per_arm,
        baseline=config.false_seen_baseline,
        effect=config.false_seen_effect,
        between_sd=config.false_seen_sd,
        within_correlation=config.within_correlation,
        n_simulations=config.n_simulations,
        alpha=config.alpha,
        seed=config.seed + 1,
    )

    icc_estimates: list[float] = []
    icc_lower: list[float] = []
    for _ in range(config.n_simulations):
        first = [rng.gauss(0.0, 1.0) for _ in range(effective_n)]
        second = [
            0.80 * value + math.sqrt(1.0 - 0.80**2) * rng.gauss(0.0, 1.0)
            for value in first
        ]
        estimate = icc_2_1(first, second)
        icc_estimates.append(estimate)
        icc_lower.append(approximate_lower_bound(estimate, effective_n, config.alpha))
    icc_power = sum(1 for bound in icc_lower if bound > 0.70) / len(icc_lower)

    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_design_power_approximation",
        "config": {
            "n_participants": config.n_participants,
            "effective_n": effective_n,
            "trials_per_cell_per_occasion": config.trials_per_cell_per_occasion,
            "occasions": config.occasions,
            "trials_per_condition": trials_per_condition,
            "n_simulations": config.n_simulations,
            "seed": config.seed,
            "alpha": config.alpha,
            "sesoi_d": config.sesoi_d,
            "baseline_accuracy": config.baseline_accuracy,
            "between_sd": config.between_sd,
            "within_correlation": config.within_correlation,
            "attrition": config.attrition,
        },
        "primary_contrast": {
            "effect_standardized": config.sesoi_d,
            "effect_raw": round(config.sesoi_d * config.between_sd, 6),
            "power": round(power, 6),
            "mean_observed_effect": round(mean_effect, 6),
        },
        "false_seen_assay": {
            "baseline": config.false_seen_baseline,
            "effect": config.false_seen_effect,
            "power": round(false_seen_power, 6),
            "mean_observed_effect": round(false_seen_mean, 6),
        },
        "reliability": {
            "true_icc": 0.80,
            "target_lower_bound": 0.70,
            "power": round(icc_power, 6),
        },
        "decision": (
            "CRT_STAGE0F_DESIGN_PASS"
            if power >= 0.90 and false_seen_power >= 0.80 and icc_power >= 0.80
            else "CRT_STAGE0F_DESIGN_REVIEW"
        ),
        "note": (
            "Planning approximation only. The registered analysis uses the CRT generative model and "
            "observed variance components; no human effect size is assumed."
        ),
    }


def run_design_power_grid(seed: int = 20261030, n_simulations: int = 120) -> dict[str, object]:
    scenarios: list[dict[str, object]] = []
    for n_participants in (160, 200, 240, 280):
        for trials in (20, 25, 30):
            for correlation in (0.3, 0.5, 0.7):
                for attrition in (0.0, 0.1, 0.2):
                    report = simulate_design_power(
                        DesignPowerConfig(
                            n_participants=n_participants,
                            trials_per_cell_per_occasion=trials,
                            within_correlation=correlation,
                            attrition=attrition,
                            n_simulations=n_simulations,
                            seed=seed + n_participants + trials * 10 + int(correlation * 10),
                        )
                    )
                    scenarios.append(
                        {
                            "n_participants": n_participants,
                            "trials_per_cell_per_occasion": trials,
                            "within_correlation": correlation,
                            "attrition": attrition,
                            "power": report["primary_contrast"]["power"],
                            "false_seen_power": report["false_seen_assay"]["power"],
                            "reliability_power": report["reliability"]["power"],
                            "decision": report["decision"],
                        }
                    )
    recommended = next(
        (
            scenario
            for scenario in scenarios
            if scenario["n_participants"] == 240
            and scenario["trials_per_cell_per_occasion"] == 25
            and scenario["within_correlation"] == 0.5
            and scenario["attrition"] == 0.1
        ),
        None,
    )
    passing = [
        scenario
        for scenario in scenarios
        if scenario["decision"] == "CRT_STAGE0F_DESIGN_PASS"
    ]
    alternatives: list[dict[str, object]] = []
    for label, n_participants, sesoi in (
        ("n_for_d020", 520, 0.20),
        ("d_for_n240", 240, 0.30),
    ):
        report = simulate_design_power(
            DesignPowerConfig(
                n_participants=n_participants,
                trials_per_cell_per_occasion=25,
                within_correlation=0.5,
                attrition=0.1,
                sesoi_d=sesoi,
                n_simulations=n_simulations,
                seed=seed + n_participants,
            )
        )
        alternatives.append(
            {
                "label": label,
                "n_participants": n_participants,
                "sesoi_d": sesoi,
                "power": report["primary_contrast"]["power"],
                "decision": report["decision"],
            }
        )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_design_power_grid",
        "seed": seed,
        "n_simulations": n_simulations,
        "n_scenarios": len(scenarios),
        "n_passing": len(passing),
        "recommended": recommended,
        "alternatives": alternatives,
        "scenarios": scenarios,
        "decision": (
            "CRT_STAGE0F_DESIGN_PASS"
            if recommended is not None and recommended["decision"] == "CRT_STAGE0F_DESIGN_PASS"
            else "CRT_STAGE0F_DESIGN_REVIEW"
        ),
        "note": (
            "Grid is a planning surface, not a substitute for the registered analysis. The recommended "
            "cell is the provisional 120-trial design at N=240 with 10% attrition."
        ),
    }


__all__ = [
    "CONDITIONS",
    "DEFAULT_TESTS",
    "BlockSpec",
    "TestSpec",
    "default_blocks",
    "source_schedule",
    "test_agency_values",
    "test_complexities",
    "test_costs",
    "yoked_test_sequence",
]

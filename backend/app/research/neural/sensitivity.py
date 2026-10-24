"""Fixed-sample sensitivity analysis for the C1 primary estimand (H2).

Because the usable participant count is fixed once data collection and QC
are done, this estimates the minimum detectable subject-level Delta_OOS
under the observed participant count, observed metric variance, the planned
paired sign-flip test, and a fixed alpha — run before the primary result is
interpreted and reported regardless of outcome, per `C1_ANALYSIS_SPEC.md`
Section 9. A null or negative primary result is not itself evidence of "no
effect" unless this analysis shows the design was adequately powered to
detect a pre-specified minimum effect of interest.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.nested_validation import sampled_sign_flip_p_value

# The smallest subject-level mean Delta_OOS this project would consider
# scientifically meaningful, fixed before inspecting any primary result.
MINIMUM_EFFECT_OF_INTEREST = 0.05


@dataclass
class SensitivityResult:
    n_participants: int
    observed_std_delta_oos: float
    alpha: float
    n_simulations: int
    power_curve: dict[str, float]  # effect size (as string key) -> estimated power
    minimum_effect_of_interest: float
    power_at_minimum_effect_of_interest: float
    adequately_powered: bool  # power_at_minimum_effect_of_interest >= 0.8

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def estimate_power_at_effect(
    true_mean_delta: float, observed_std: float, n_participants: int,
    alpha: float = 0.05, n_simulations: int = 2000, seed: int = 42,
    p_value_n_samples: int = 2000,
) -> float:
    """Simulated power: fraction of simulated datasets (Gaussian
    per-participant deltas at the given true mean and the OBSERVED standard
    deviation) for which the sign-flip test rejects at `alpha`.

    Uses the Monte Carlo sign-flip approximation (`sampled_sign_flip_p_value`)
    rather than exact enumeration for the per-replication p-value: a power
    simulation already runs hundreds-to-thousands of outer replications, so
    exact enumeration per replication (2**n_participants terms each) is
    computationally infeasible while adding no precision that matters at this
    scale -- the outer Monte Carlo loop is itself already an approximation."""
    rng = np.random.RandomState(seed)
    rejections = 0
    for i in range(n_simulations):
        deltas = rng.normal(loc=true_mean_delta, scale=observed_std, size=n_participants)
        p = sampled_sign_flip_p_value(deltas, n_samples=p_value_n_samples, seed=seed * 100_000 + i)
        if p < alpha:
            rejections += 1
    return rejections / n_simulations


def run_sensitivity_analysis(
    n_participants: int, observed_std_delta_oos: float,
    effect_grid: tuple[float, ...] = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10),
    alpha: float = 0.05, n_simulations: int = 2000, seed: int = 42,
) -> SensitivityResult:
    power_curve = {
        f"{effect:.3f}": estimate_power_at_effect(
            effect, observed_std_delta_oos, n_participants, alpha=alpha, n_simulations=n_simulations, seed=seed,
        )
        for effect in effect_grid
    }
    power_at_min = estimate_power_at_effect(
        MINIMUM_EFFECT_OF_INTEREST, observed_std_delta_oos, n_participants,
        alpha=alpha, n_simulations=n_simulations, seed=seed,
    )
    return SensitivityResult(
        n_participants=n_participants, observed_std_delta_oos=observed_std_delta_oos,
        alpha=alpha, n_simulations=n_simulations, power_curve=power_curve,
        minimum_effect_of_interest=MINIMUM_EFFECT_OF_INTEREST,
        power_at_minimum_effect_of_interest=power_at_min,
        adequately_powered=power_at_min >= 0.8,
    )

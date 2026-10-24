from __future__ import annotations

import math


def required_sample_size(
    effect_size_d: float = 0.50,
    alpha: float = 0.05,
    power: float = 0.80,
    n_conditions: int = 3,
    n_timepoints: int = 3,
    rho: float = 0.50,
    dropout_rate: float = 0.15,
) -> dict:
    """Approximate sample-size estimate for a within-subject repeated-measures design.

    Uses the Huynh-Feldt-corrected F-test approximation for group x time interaction
    in a mixed/within-subjects design. This is a planning heuristic, not a replacement
    for formal simulation-based power analysis (e.g. simr in R).
    """
    z_alpha = _z_score(1.0 - alpha / 2.0)
    z_beta = _z_score(power)

    n_base = ((z_alpha + z_beta) / effect_size_d) ** 2

    rm_correction = 1.0 - rho
    n_adjusted = n_base * rm_correction

    df_interaction = (n_conditions - 1) * (n_timepoints - 1)
    design_factor = max(1.0, math.sqrt(df_interaction / 2.0))
    n_per_group = math.ceil(n_adjusted * design_factor)

    n_with_dropout = math.ceil(n_per_group / (1.0 - dropout_rate))

    return {
        "effect_size_d": effect_size_d,
        "alpha": alpha,
        "power": power,
        "n_conditions": n_conditions,
        "n_timepoints": n_timepoints,
        "assumed_correlation_rho": rho,
        "dropout_rate": dropout_rate,
        "n_per_sequence_raw": n_per_group,
        "n_per_sequence_with_dropout": n_with_dropout,
        "total_participants": n_with_dropout,
        "total_sessions": n_with_dropout * n_conditions * n_timepoints,
        "method": "approximate_within_subjects_ftest",
        "note": (
            "This is a planning heuristic. For publication, use simulation-based "
            "power analysis (e.g. simr in R) with pilot data."
        ),
    }


def _z_score(quantile: float) -> float:
    """Approximate z-score using Abramowitz & Stegun rational approximation."""
    if quantile <= 0.0 or quantile >= 1.0:
        raise ValueError("Quantile must be in (0, 1)")

    t = math.sqrt(-2.0 * math.log(1.0 - quantile)) if quantile > 0.5 else math.sqrt(-2.0 * math.log(quantile))

    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    return z if quantile > 0.5 else -z


def sensitivity_table(
    n_values: list[int] | None = None,
    effect_sizes: list[float] | None = None,
) -> list[dict]:
    if n_values is None:
        n_values = [12, 18, 24, 30, 36]
    if effect_sizes is None:
        effect_sizes = [0.30, 0.40, 0.50, 0.60, 0.80]

    results = []
    for n in n_values:
        for d in effect_sizes:
            info = required_sample_size(effect_size_d=d)
            results.append({
                "n_target": n,
                "effect_size_d": d,
                "n_required": info["n_per_sequence_with_dropout"],
                "sufficient": n >= info["n_per_sequence_with_dropout"],
            })
    return results

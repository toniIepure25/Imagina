from __future__ import annotations

import math
from collections import defaultdict


def aggregate_by_condition(trials: list[dict]) -> dict:
    """Compute descriptive statistics for each condition."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for t in trials:
        grouped[t["condition"]].append(t)

    results = {}
    for condition, rows in grouped.items():
        results[condition] = {
            "n_trials": len(rows),
            "n_participants": len({r["participant_id"] for r in rows}),
            "vividness": _describe([r["vividness"] for r in rows]),
            "confidence": _describe([r["confidence"] for r in rows]),
            "iqi": _describe([r["iqi"] for r in rows]),
            "pid": _describe([r["pid"] for r in rows]),
        }
    return results


def compute_condition_means_by_session(trials: list[dict]) -> list[dict]:
    """Compute per-participant, per-condition, per-session means."""
    def key_fn(t: dict) -> tuple:
        return (t["participant_id"], t["condition"], t["session_index"])
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for t in trials:
        grouped[key_fn(t)].append(t)

    results = []
    for (pid, cond, sidx), rows in sorted(grouped.items()):
        results.append({
            "participant_id": pid,
            "condition": cond,
            "session_index": sidx,
            "n_trials": len(rows),
            "mean_vividness": _mean([r["vividness"] for r in rows]),
            "mean_confidence": _mean([r["confidence"] for r in rows]),
            "mean_iqi": _mean([r["iqi"] for r in rows]),
            "mean_pid": _mean([r["pid"] for r in rows]),
        })
    return results


def compute_cohens_d(group1: list[float], group2: list[float]) -> float:
    """Cohen's d for independent samples."""
    m1 = _mean(group1)
    m2 = _mean(group2)
    s1 = _std(group1)
    s2 = _std(group2)
    n1 = len(group1)
    n2 = len(group2)
    pooled_sd = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return 0.0
    return (m1 - m2) / pooled_sd


def validate_iqi_pid_relationship(trials: list[dict]) -> dict:
    """Check expected inverse relationship between IQI and PID."""
    iqis = [t["iqi"] for t in trials]
    pids = [t["pid"] for t in trials]
    r = _pearson_r(iqis, pids)
    return {
        "pearson_r": round(r, 4),
        "expected_negative": r < 0,
        "n_trials": len(trials),
        "interpretation": "consistent" if r < -0.2 else "weak_or_inconsistent",
    }


def lmm_specification() -> dict:
    """Return the specification for the planned Linear Mixed-Effects Model.

    This describes the model structure for implementation in R (lme4) or Python (statsmodels).
    The actual fitting requires real data and appropriate statistical software.
    """
    return {
        "model_family": "Linear Mixed-Effects Model (LMM)",
        "implementation": "R: lmer(dv ~ condition * session + (1 + session | participant_id))",
        "dependent_variables": [
            {
                "name": "vividness",
                "type": "ordinal_treated_as_continuous",
                "range": "1-7",
                "primary": True,
            },
            {
                "name": "iqi",
                "type": "continuous",
                "range": "0-1",
                "primary": False,
                "note": "Exploratory proxy, not a validated outcome.",
            },
            {
                "name": "pid",
                "type": "continuous",
                "range": "0-1",
                "primary": False,
                "note": "Exploratory proxy, not a validated outcome.",
            },
        ],
        "fixed_effects": [
            "condition (adaptive vs fixed vs yoked)",
            "session (1..N, within condition)",
            "condition x session interaction",
        ],
        "random_effects": [
            "(1 + session | participant_id)",
        ],
        "covariates": [
            "pre_vviq2 (baseline imagery ability)",
            "session_order (counterbalancing check)",
        ],
        "contrasts": [
            "adaptive vs fixed (tests contingency beyond practice)",
            "adaptive vs yoked (tests contingency beyond non-contingent feedback)",
            "fixed vs yoked (tests presence of feedback vs sham)",
        ],
        "correction": "Bonferroni or Holm for 3 planned contrasts",
        "effect_size": "Cohen's d from model estimates",
        "missing_data": "FIML (full information maximum likelihood)",
        "assumption_checks": [
            "Residual normality (Q-Q plot)",
            "Homoscedasticity (residual vs fitted)",
            "Random effects distribution",
        ],
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _describe(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    return {
        "mean": round(_mean(values), 4),
        "std": round(_std(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "n": len(values),
    }


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)

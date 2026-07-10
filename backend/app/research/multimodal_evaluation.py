from __future__ import annotations

import math


def compute_modality_baselines(trials: list[dict]) -> dict:
    """Compute baseline statistics per modality (self-report, behavioral, proxy)."""
    modalities = {
        "self_report": {
            "variables": ["vividness", "confidence", "effort"],
            "description": "Trial-level Likert ratings collected during imagery tasks.",
        },
        "behavioral": {
            "variables": ["behavioral_consistency"],
            "description": "Response timing and behavioral pattern consistency.",
        },
        "proxy_metric": {
            "variables": ["iqi", "pid"],
            "description": "IQI/PID composite proxies. Exploratory, not validated.",
        },
    }

    results = {}
    for modality_name, info in modalities.items():
        var_stats = {}
        for var in info["variables"]:
            values = [t[var] for t in trials if var in t]
            var_stats[var] = _describe(values) if values else _describe([])
        results[modality_name] = {
            "description": info["description"],
            "variables": var_stats,
        }
    return results


def compute_convergent_validity(trials: list[dict]) -> dict:
    """Check correlations between modalities that should theoretically converge."""
    vividness = [t.get("vividness", 0) for t in trials]
    confidence = [t.get("confidence", 0) for t in trials]
    iqi = [t.get("iqi", 0) for t in trials]
    pid = [t.get("pid", 0) for t in trials]
    behavioral = [t.get("behavioral_consistency", 0) for t in trials]

    return {
        "n_trials": len(trials),
        "correlations": {
            "vividness_confidence": _safe_pearson(vividness, confidence),
            "vividness_iqi": _safe_pearson(vividness, iqi),
            "vividness_pid": _safe_pearson(vividness, pid),
            "iqi_pid": _safe_pearson(iqi, pid),
            "behavioral_iqi": _safe_pearson(behavioral, iqi),
            "behavioral_vividness": _safe_pearson(behavioral, vividness),
        },
        "expected_directions": {
            "vividness_confidence": "positive",
            "vividness_iqi": "positive",
            "vividness_pid": "negative",
            "iqi_pid": "negative",
            "behavioral_iqi": "positive",
            "behavioral_vividness": "positive",
        },
    }


def compute_incremental_validity_summary(trials: list[dict]) -> dict:
    """Summarize incremental validity analysis structure.

    Actual incremental validity (hierarchical regression) requires R/Python
    statistical packages. This returns the specification and exploratory checks.
    """
    n_trials = len(trials)
    conditions = list({t.get("condition", "unknown") for t in trials})

    condition_effect_sizes = {}
    for cond in conditions:
        cond_trials = [t for t in trials if t.get("condition") == cond]
        if len(cond_trials) < 2:
            continue
        early = [
            t["vividness"] for t in cond_trials
            if t.get("session_index", 0) == 0
        ]
        late = [
            t["vividness"] for t in cond_trials
            if t.get("session_index", 0) == max(t.get("session_index", 0) for t in cond_trials)
        ]
        if early and late:
            condition_effect_sizes[cond] = {
                "early_mean": round(_mean(early), 3),
                "late_mean": round(_mean(late), 3),
                "improvement": round(_mean(late) - _mean(early), 3),
            }

    return {
        "n_trials": n_trials,
        "n_conditions": len(conditions),
        "conditions": conditions,
        "condition_improvements": condition_effect_sizes,
        "incremental_validity_specification": {
            "method": "Hierarchical linear regression / LMM comparison",
            "step_1": "Self-report only (vividness ~ condition * session)",
            "step_2": "Add behavioral (vividness ~ condition * session + behavioral_consistency)",
            "step_3": "Add proxy metrics (vividness ~ condition * session + behavioral_consistency + iqi)",
            "comparison": "Likelihood ratio test or AIC/BIC comparison between steps",
            "interpretation": (
                "If Step 2 or Step 3 significantly improves model fit, "
                "the added modality provides incremental validity."
            ),
        },
        "note": (
            "Incremental validity testing requires real participant data and "
            "appropriate statistical software (R lme4 or Python statsmodels)."
        ),
    }


def group_aware_evaluation(trials: list[dict], participants: list[dict]) -> dict:
    """Check for baseline-dependent effects (e.g. low vs high imagers)."""
    p_vviq = {p["participant_id"]: p.get("pre_vviq2", 0) for p in participants}

    median_vviq = _median(list(p_vviq.values())) if p_vviq else 48

    low_imagers = {pid for pid, v in p_vviq.items() if v < median_vviq}
    high_imagers = {pid for pid, v in p_vviq.items() if v >= median_vviq}

    low_trials = [t for t in trials if t["participant_id"] in low_imagers]
    high_trials = [t for t in trials if t["participant_id"] in high_imagers]

    return {
        "median_vviq2": median_vviq,
        "n_low_imagers": len(low_imagers),
        "n_high_imagers": len(high_imagers),
        "low_imagers": {
            "mean_vividness": round(_mean([t["vividness"] for t in low_trials]), 3) if low_trials else 0,
            "mean_iqi": round(_mean([t["iqi"] for t in low_trials]), 3) if low_trials else 0,
        },
        "high_imagers": {
            "mean_vividness": round(_mean([t["vividness"] for t in high_trials]), 3) if high_trials else 0,
            "mean_iqi": round(_mean([t["iqi"] for t in high_trials]), 3) if high_trials else 0,
        },
        "note": "Median split is exploratory. Formal analysis should use VVIQ-2 as a continuous covariate.",
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


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


def _safe_pearson(xs: list[float], ys: list[float]) -> dict:
    n = min(len(xs), len(ys))
    if n < 3:
        return {"r": 0.0, "n": n, "interpretable": False}
    xs_t = xs[:n]
    ys_t = ys[:n]
    r = _pearson_r(xs_t, ys_t)
    return {"r": round(r, 4), "n": n, "interpretable": n >= 10}


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    mx = _mean(xs)
    my = _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)

"""Confirmatory hierarchical endpoint analysis.

Implements the prespecified trial-level hierarchical model using statsmodels
MixedLM. Includes convergence diagnostics, fallback behavior, and
standardized result reporting.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

MODEL_SPEC_VERSION = "1.0"

PRIMARY_MODEL_FORMULA = (
    "composite_error ~ C(condition, Treatment(reference='yoked'))"
    " + period + session_index + baseline_precision"
    " + C(task_family)"
)

FALLBACK_MODEL_FORMULA = (
    "composite_error ~ C(condition, Treatment(reference='yoked'))"
    " + session_index + baseline_precision"
)


@dataclass
class AnalysisResult:
    estimand_id: str
    model_formula: str
    model_type: str
    effect_estimate: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    test_statistic: float
    p_value: float
    standardized_effect: float
    converged: bool
    singularity_warning: bool
    n_participants: int
    n_trials: int
    n_missing: int
    analysis_population: str
    model_spec_hash: str
    is_fallback: bool
    residual_diagnostics: dict[str, float] = field(default_factory=dict)
    random_effects_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def run_primary_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str = "ate_adaptive_vs_yoked",
    alpha: float = 0.05,
) -> AnalysisResult:
    """Run the prespecified confirmatory analysis on trial-level data."""
    try:
        import pandas as pd
        import statsmodels.formula.api as smf
    except ImportError:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    df = pd.DataFrame(trial_data)
    if df.empty or len(df["participant_id"].unique()) < 3:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    required = ["composite_error", "condition", "participant_id"]
    for col in required:
        if col not in df.columns:
            return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    for col in ["period", "session_index", "baseline_precision", "task_family"]:
        if col not in df.columns:
            df[col] = 0 if col != "task_family" else "feature_reconstruction"

    formula = PRIMARY_MODEL_FORMULA
    is_fallback = False
    converged = True
    singularity = False

    try:
        model = smf.mixedlm(
            formula, df, groups=df["participant_id"],
            re_formula="~1",
        )
        result = model.fit(reml=True, method="lbfgs", maxiter=200)
        converged = result.converged
    except Exception:
        try:
            formula = FALLBACK_MODEL_FORMULA
            is_fallback = True
            model = smf.mixedlm(
                formula, df, groups=df["participant_id"],
                re_formula="~1",
            )
            result = model.fit(reml=True, method="lbfgs", maxiter=200)
            converged = result.converged
        except Exception:
            return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    contrast_name = None
    for param in result.params.index:
        if "adaptive" in str(param).lower():
            contrast_name = param
            break

    if contrast_name is None:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    effect = float(result.params[contrast_name])
    se = float(result.bse[contrast_name])
    z_crit = 1.96
    ci_lo = effect - z_crit * se
    ci_hi = effect + z_crit * se
    z_stat = effect / se if se > 0 else 0.0
    p_val = float(result.pvalues[contrast_name])

    resid = result.resid
    residual_sd = float(resid.std()) if len(resid) > 0 else 1.0
    std_effect = effect / residual_sd if residual_sd > 0 else 0.0

    n_participants = len(df["participant_id"].unique())
    n_trials = len(df)
    n_missing = int(df["composite_error"].isna().sum())

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=formula,
        model_type="statsmodels.MixedLM",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(ci_lo, 6),
        ci_upper=round(ci_hi, 6),
        test_statistic=round(z_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(std_effect, 4),
        converged=converged,
        singularity_warning=singularity,
        n_participants=n_participants,
        n_trials=n_trials,
        n_missing=n_missing,
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(formula),
        is_fallback=is_fallback,
        residual_diagnostics={
            "residual_mean": round(float(resid.mean()), 6),
            "residual_sd": round(residual_sd, 6),
        },
    )


def _fallback_aggregate_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str,
    alpha: float,
) -> AnalysisResult:
    """Participant-level aggregation fallback when MixedLM fails."""
    from collections import defaultdict

    by_participant: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for t in trial_data:
        by_participant[t["participant_id"]][t["condition"]].append(t["composite_error"])

    adaptive_means: list[float] = []
    yoked_means: list[float] = []
    for pid, conds in by_participant.items():
        if "adaptive" in conds and "yoked" in conds:
            adaptive_means.append(sum(conds["adaptive"]) / len(conds["adaptive"]))
            yoked_means.append(sum(conds["yoked"]) / len(conds["yoked"]))

    if len(adaptive_means) < 2:
        return AnalysisResult(
            estimand_id=estimand_id, model_formula="participant_aggregation",
            model_type="fallback_paired_t", effect_estimate=0.0, standard_error=1.0,
            ci_lower=-1.0, ci_upper=1.0, test_statistic=0.0, p_value=1.0,
            standardized_effect=0.0, converged=False, singularity_warning=False,
            n_participants=len(adaptive_means), n_trials=len(trial_data), n_missing=0,
            analysis_population="intention_to_treat", model_spec_hash="fallback", is_fallback=True,
        )

    n = len(adaptive_means)
    diffs = [a - y for a, y in zip(adaptive_means, yoked_means)]
    mean_diff = sum(diffs) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1) if n > 1 else 1.0
    se = math.sqrt(var_diff / n)
    t_stat = mean_diff / se if se > 0 else 0.0

    pooled_sd = math.sqrt(
        (sum((a - sum(adaptive_means) / n) ** 2 for a in adaptive_means)
         + sum((y - sum(yoked_means) / n) ** 2 for y in yoked_means)) / (2 * n - 2)
    ) if n > 1 else 1.0
    std_effect = mean_diff / pooled_sd if pooled_sd > 0 else 0.0

    t_crit = 2.0
    ci_lo = mean_diff - t_crit * se
    ci_hi = mean_diff + t_crit * se

    from scipy.stats import t as t_dist
    p_val = float(2 * t_dist.sf(abs(t_stat), df=n - 1))

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula="participant_aggregation_paired_t",
        model_type="fallback_paired_t",
        effect_estimate=round(mean_diff, 6),
        standard_error=round(se, 6),
        ci_lower=round(ci_lo, 6),
        ci_upper=round(ci_hi, 6),
        test_statistic=round(t_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(std_effect, 4),
        converged=True,
        singularity_warning=False,
        n_participants=n,
        n_trials=len(trial_data),
        n_missing=0,
        analysis_population="intention_to_treat",
        model_spec_hash="fallback_paired_t",
        is_fallback=True,
    )


def _spec_hash(formula: str) -> str:
    return hashlib.sha256(
        json.dumps({"formula": formula, "version": MODEL_SPEC_VERSION},
                   sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

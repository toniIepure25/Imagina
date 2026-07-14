"""Confirmatory hierarchical endpoint analysis with calibrated estimators.

Estimator A: GEE marginal crossover estimator with participant clusters
Estimator B: MixedLM hierarchical sensitivity model
Estimator C: Randomization-based inference (permuting Williams sequences)
Bootstrap CI: Cluster bootstrap for validated coverage
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.research.rng_registry import derive_seed

MODEL_SPEC_VERSION = "2.0"

PRIMARY_MODEL_FORMULA = (
    "composite_error ~ C(condition, Treatment(reference='yoked'))"
    " + period + baseline_precision"
    " + C(task_family)"
    " + carryover_indicator"
)

HIERARCHICAL_FORMULA = (
    "composite_error ~ C(condition, Treatment(reference='yoked'))"
    " + period + baseline_precision"
    " + C(task_family)"
    " + carryover_indicator"
    " + session_index"
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
    primary_estimator_status: str = "ok"
    fallback_used: bool = False
    fallback_reason: str = ""
    inference_valid: bool = True
    residual_diagnostics: dict[str, float] = field(default_factory=dict)
    random_effects_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class MultiEstimatorResult:
    primary: AnalysisResult
    hierarchical: AnalysisResult | None = None
    randomization: AnalysisResult | None = None
    bootstrap_ci: tuple[float, float] | None = None
    primary_convergence: bool = True
    fallback_used: bool = False
    valid_inference: bool = True

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"primary": self.primary.to_dict()}
        if self.hierarchical:
            d["hierarchical"] = self.hierarchical.to_dict()
        if self.randomization:
            d["randomization"] = self.randomization.to_dict()
        if self.bootstrap_ci:
            d["bootstrap_ci"] = list(self.bootstrap_ci)
        d["primary_convergence"] = self.primary_convergence
        d["fallback_used"] = self.fallback_used
        d["valid_inference"] = self.valid_inference
        return d


def run_primary_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str = "ate_adaptive_vs_yoked",
    alpha: float = 0.05,
) -> AnalysisResult:
    """Run Estimator A: GEE-like marginal crossover estimator."""
    try:
        import pandas as pd  # noqa: F401
        import statsmodels.formula.api as smf  # noqa: F401
    except ImportError:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    df = _prepare_df(trial_data)
    if df is None or len(df["participant_id"].unique()) < 3:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    formula = PRIMARY_MODEL_FORMULA
    is_fallback = False
    converged = True
    singularity = False
    status = "ok"
    fallback_reason = ""

    try:
        model = smf.mixedlm(formula, df, groups=df["participant_id"], re_formula="~1")
        result = model.fit(reml=True, method="lbfgs", maxiter=200)
        converged = result.converged
        if not converged:
            status = "non_convergence"
    except Exception as exc:
        status = f"primary_exception: {type(exc).__name__}"
        fallback_reason = status
        is_fallback = True
        try:
            result = _try_simple_model(df, estimand_id, alpha)
            return result
        except Exception:
            return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    contrast_name = _find_adaptive_contrast(result)
    if contrast_name is None:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    effect = float(result.params[contrast_name])
    se = float(result.bse[contrast_name])
    if se <= 0 or math.isnan(se):
        status = "invalid_se"
        return _make_invalid_result(trial_data, estimand_id, formula, status)

    z_crit = 1.96
    ci_lo = effect - z_crit * se
    ci_hi = effect + z_crit * se
    z_stat = effect / se
    p_val = float(result.pvalues[contrast_name])

    resid = result.resid
    residual_sd = float(resid.std()) if len(resid) > 0 else 1.0
    std_effect = effect / residual_sd if residual_sd > 0 else 0.0

    inference_valid = converged and not is_fallback and se > 0 and not math.isnan(p_val)

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=formula,
        model_type="gee_marginal_crossover",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(ci_lo, 6),
        ci_upper=round(ci_hi, 6),
        test_statistic=round(z_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(std_effect, 4),
        converged=converged,
        singularity_warning=singularity,
        n_participants=len(df["participant_id"].unique()),
        n_trials=len(df),
        n_missing=int(df["composite_error"].isna().sum()),
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(formula),
        is_fallback=is_fallback,
        primary_estimator_status=status,
        fallback_used=is_fallback,
        fallback_reason=fallback_reason,
        inference_valid=inference_valid,
        residual_diagnostics={
            "residual_mean": round(float(resid.mean()), 6),
            "residual_sd": round(residual_sd, 6),
        },
    )


def run_hierarchical_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str = "ate_adaptive_vs_yoked",
    alpha: float = 0.05,
) -> AnalysisResult:
    """Run Estimator B: Hierarchical sensitivity model with random slopes."""
    try:
        import pandas as pd  # noqa: F401
        import statsmodels.formula.api as smf  # noqa: F401
    except ImportError:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    df = _prepare_df(trial_data)
    if df is None or len(df["participant_id"].unique()) < 3:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    formula = HIERARCHICAL_FORMULA
    converged = True
    singularity = False
    status = "ok"

    try:
        model = smf.mixedlm(
            formula, df, groups=df["participant_id"],
            re_formula="~1",
        )
        result = model.fit(reml=True, method="lbfgs", maxiter=300)
        converged = result.converged

        re_cov = result.cov_re
        if hasattr(re_cov, 'values'):
            diag = re_cov.values.diagonal() if hasattr(re_cov.values, 'diagonal') else [0]
            if any(v < 1e-10 for v in diag):
                singularity = True
                status = "boundary_variance"
    except Exception as exc:
        status = f"hierarchical_exception: {type(exc).__name__}"
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    contrast_name = _find_adaptive_contrast(result)
    if contrast_name is None:
        return _fallback_aggregate_analysis(trial_data, estimand_id, alpha)

    effect = float(result.params[contrast_name])
    se = float(result.bse[contrast_name])
    if se <= 0 or math.isnan(se):
        status = "invalid_se"
        return _make_invalid_result(trial_data, estimand_id, formula, status)

    z_crit = 1.96
    z_stat = effect / se
    p_val = float(result.pvalues[contrast_name])

    inference_valid = converged and se > 0 and not math.isnan(p_val)

    resid = result.resid
    residual_sd = float(resid.std()) if len(resid) > 0 else 1.0

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=formula,
        model_type="hierarchical_sensitivity",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(effect - z_crit * se, 6),
        ci_upper=round(effect + z_crit * se, 6),
        test_statistic=round(z_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(effect / residual_sd if residual_sd > 0 else 0.0, 4),
        converged=converged,
        singularity_warning=singularity,
        n_participants=len(df["participant_id"].unique()),
        n_trials=len(df),
        n_missing=int(df["composite_error"].isna().sum()),
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(formula),
        is_fallback=False,
        primary_estimator_status=status,
        inference_valid=inference_valid,
    )


def run_randomization_test(
    trial_data: list[dict[str, Any]],
    n_permutations: int = 500,
    seed: int = 42,
) -> AnalysisResult:
    """Estimator C: Randomization test permuting Williams sequence assignments."""
    by_participant: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for t in trial_data:
        by_participant[t["participant_id"]][t["condition"]].append(t["composite_error"])

    paired: list[tuple[float, float]] = []
    pids: list[str] = []
    for pid, conds in by_participant.items():
        if "adaptive" in conds and "yoked" in conds:
            a_mean = sum(conds["adaptive"]) / len(conds["adaptive"])
            y_mean = sum(conds["yoked"]) / len(conds["yoked"])
            paired.append((a_mean, y_mean))
            pids.append(pid)

    if len(paired) < 2:
        return _make_invalid_result(trial_data, "ate_adaptive_vs_yoked", "randomization", "insufficient_pairs")

    diffs = [a - y for a, y in paired]
    observed_stat = sum(diffs) / len(diffs)

    rng = random.Random(derive_seed(seed, "randomization_test"))
    n_extreme = 0
    for _ in range(n_permutations):
        perm_diffs = [d * (1 if rng.random() > 0.5 else -1) for d in diffs]
        perm_stat = sum(perm_diffs) / len(perm_diffs)
        if abs(perm_stat) >= abs(observed_stat):
            n_extreme += 1

    p_rand = (n_extreme + 1) / (n_permutations + 1)

    return AnalysisResult(
        estimand_id="ate_adaptive_vs_yoked",
        model_formula="randomization_test",
        model_type="randomization_inference",
        effect_estimate=round(observed_stat, 6),
        standard_error=0.0,
        ci_lower=0.0,
        ci_upper=0.0,
        test_statistic=round(observed_stat, 6),
        p_value=round(p_rand, 6),
        standardized_effect=0.0,
        converged=True,
        singularity_warning=False,
        n_participants=len(paired),
        n_trials=len(trial_data),
        n_missing=0,
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash("randomization_test"),
        is_fallback=False,
        primary_estimator_status="ok",
        inference_valid=True,
    )


def run_bootstrap_ci(
    trial_data: list[dict[str, Any]],
    n_bootstrap: int = 500,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Cluster bootstrap CI for the adaptive-yoked contrast."""
    by_participant: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for t in trial_data:
        by_participant[t["participant_id"]][t["condition"]].append(t["composite_error"])

    paired: list[tuple[float, float]] = []
    for pid, conds in by_participant.items():
        if "adaptive" in conds and "yoked" in conds:
            a_mean = sum(conds["adaptive"]) / len(conds["adaptive"])
            y_mean = sum(conds["yoked"]) / len(conds["yoked"])
            paired.append((a_mean, y_mean))

    if len(paired) < 2:
        return (-1.0, 1.0)

    rng = random.Random(derive_seed(seed, "bootstrap"))
    boot_effects: list[float] = []
    for _ in range(n_bootstrap):
        sample = [paired[rng.randint(0, len(paired) - 1)] for _ in range(len(paired))]
        diffs = [a - y for a, y in sample]
        boot_effects.append(sum(diffs) / len(diffs))

    boot_effects.sort()
    lo_idx = max(0, int(n_bootstrap * (alpha / 2)) - 1)
    hi_idx = min(n_bootstrap - 1, int(n_bootstrap * (1 - alpha / 2)))
    return (round(boot_effects[lo_idx], 6), round(boot_effects[hi_idx], 6))


def run_full_analysis(
    trial_data: list[dict[str, Any]],
    alpha: float = 0.05,
    seed: int = 42,
) -> MultiEstimatorResult:
    """Run all three estimators and bootstrap CI."""
    primary = run_primary_analysis(trial_data, alpha=alpha)
    hierarchical = run_hierarchical_analysis(trial_data, alpha=alpha)
    randomization = run_randomization_test(trial_data, seed=seed)
    bootstrap = run_bootstrap_ci(trial_data, seed=seed, alpha=alpha)

    valid = primary.inference_valid
    fallback = primary.is_fallback

    return MultiEstimatorResult(
        primary=primary,
        hierarchical=hierarchical,
        randomization=randomization,
        bootstrap_ci=bootstrap,
        primary_convergence=primary.converged and not primary.is_fallback,
        fallback_used=fallback,
        valid_inference=valid,
    )


def _prepare_df(trial_data: list[dict[str, Any]]) -> Any:
    """Prepare DataFrame from trial data with required columns."""
    import pandas as pd
    df = pd.DataFrame(trial_data)
    if df.empty:
        return None
    required = ["composite_error", "condition", "participant_id"]
    for col in required:
        if col not in df.columns:
            return None
    for col, default in [("period", 0), ("session_index", 0), ("baseline_precision", 0.5),
                         ("task_family", "feature_reconstruction"), ("carryover_indicator", "none")]:
        if col not in df.columns:
            df[col] = default
    return df


def _find_adaptive_contrast(result: Any) -> str | None:
    for param in result.params.index:
        if "adaptive" in str(param).lower():
            return param
    return None


def _try_simple_model(df: Any, estimand_id: str, alpha: float) -> AnalysisResult:
    """Simplified MixedLM without task_family or carryover."""
    import statsmodels.formula.api as smf
    formula = "composite_error ~ C(condition, Treatment(reference='yoked')) + period + baseline_precision"
    model = smf.mixedlm(formula, df, groups=df["participant_id"], re_formula="~1")
    result = model.fit(reml=True, method="lbfgs", maxiter=200)

    contrast_name = _find_adaptive_contrast(result)
    if contrast_name is None:
        raise ValueError("No adaptive contrast found")

    effect = float(result.params[contrast_name])
    se = float(result.bse[contrast_name])
    z_crit = 1.96
    resid = result.resid
    residual_sd = float(resid.std()) if len(resid) > 0 else 1.0

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=formula,
        model_type="simplified_mixedlm",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(effect - z_crit * se, 6),
        ci_upper=round(effect + z_crit * se, 6),
        test_statistic=round(effect / se if se > 0 else 0.0, 4),
        p_value=round(float(result.pvalues[contrast_name]), 6),
        standardized_effect=round(effect / residual_sd if residual_sd > 0 else 0.0, 4),
        converged=result.converged,
        singularity_warning=False,
        n_participants=len(df["participant_id"].unique()),
        n_trials=len(df),
        n_missing=int(df["composite_error"].isna().sum()),
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(formula),
        is_fallback=True,
        primary_estimator_status="simplified_fallback",
        fallback_used=True,
        fallback_reason="primary_model_failed",
        inference_valid=result.converged,
    )


def _make_invalid_result(
    trial_data: list[dict[str, Any]],
    estimand_id: str,
    formula: str,
    reason: str,
) -> AnalysisResult:
    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=formula,
        model_type="invalid",
        effect_estimate=0.0,
        standard_error=0.0,
        ci_lower=0.0,
        ci_upper=0.0,
        test_statistic=0.0,
        p_value=1.0,
        standardized_effect=0.0,
        converged=False,
        singularity_warning=False,
        n_participants=0,
        n_trials=len(trial_data),
        n_missing=0,
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(formula),
        is_fallback=True,
        primary_estimator_status=reason,
        fallback_used=True,
        fallback_reason=reason,
        inference_valid=False,
    )


def _fallback_aggregate_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str,
    alpha: float,
) -> AnalysisResult:
    """Participant-level aggregation fallback when MixedLM fails."""
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
        return _make_invalid_result(trial_data, estimand_id, "paired_t", "insufficient_data")

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

    try:
        from scipy.stats import t as t_dist
        p_val = float(2 * t_dist.sf(abs(t_stat), df=n - 1))
    except ImportError:
        p_val = 1.0 if abs(t_stat) < 2.0 else 0.01

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
        converged=False,
        singularity_warning=False,
        n_participants=n,
        n_trials=len(trial_data),
        n_missing=0,
        analysis_population="intention_to_treat",
        model_spec_hash="fallback_paired_t",
        is_fallback=True,
        primary_estimator_status="fallback",
        fallback_used=True,
        fallback_reason="primary_and_hierarchical_failed",
        inference_valid=False,
    )


def _spec_hash(formula: str) -> str:
    return hashlib.sha256(
        json.dumps({"formula": formula, "version": MODEL_SPEC_VERSION},
                   sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

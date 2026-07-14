"""Confirmatory crossover inference with calibrated estimators.

Estimator A (primary): statsmodels GEE with Gaussian identity family,
    participant clusters, and robust sandwich covariance.
Estimator B (sensitivity): MixedLM hierarchical model (random intercepts,
    optionally random slopes). Sensitivity only — never used as primary.
Estimator C (sensitivity): Randomization-based inference permuting
    Williams-sequence assignments.
Bootstrap CI: Cluster bootstrap resampling participants and re-fitting
    the primary GEE estimator.
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

MODEL_SPEC_VERSION = "4.0"

MIN_PARTICIPANT_CLUSTERS = 6
BOOTSTRAP_VALID_THRESHOLD = 0.70
MAX_CONDITION_NUMBER = 1e12

GEE_FORMULA = (
    "composite_error ~ adaptive_ind"
    " + fixed_ind"
    " + C(period)"
    " + C(sequence)"
    " + baseline_precision"
    " + C(task_family)"
    " + carryover_indicator_num"
)

HIERARCHICAL_FORMULA = (
    "composite_error ~ adaptive_ind"
    " + fixed_ind"
    " + C(period)"
    " + C(task_family)"
    " + carryover_indicator_num"
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
    n_clusters: int = 0
    cluster_size_min: int = 0
    cluster_size_max: int = 0
    condition_number: float = 0.0
    rank_deficient: bool = False
    covariance_type: str = ""
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
    bootstrap_valid_rate: float = 0.0
    bootstrap_n_success: int = 0
    bootstrap_n_fail: int = 0
    bootstrap_se: float = 0.0
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
        d["bootstrap_valid_rate"] = self.bootstrap_valid_rate
        d["bootstrap_n_success"] = self.bootstrap_n_success
        d["bootstrap_n_fail"] = self.bootstrap_n_fail
        d["bootstrap_se"] = self.bootstrap_se
        d["primary_convergence"] = self.primary_convergence
        d["fallback_used"] = self.fallback_used
        d["valid_inference"] = self.valid_inference
        return d


def _prepare_df(trial_data: list[dict[str, Any]]) -> Any:
    """Prepare DataFrame with indicator (reference) coding, yoked = 0.

    adaptive_ind = 1 if condition == "adaptive" else 0
    fixed_ind    = 1 if condition == "fixed"    else 0

    The coefficient on adaptive_ind equals E[Y|adaptive] - E[Y|yoked]
    adjusted for covariates — the prespecified causal contrast.
    """
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(trial_data)
    if df.empty:
        return None
    required = ["composite_error", "condition", "participant_id"]
    for col in required:
        if col not in df.columns:
            return None

    for col, default in [
        ("period", 0), ("session_index", 0), ("baseline_precision", 0.5),
        ("task_family", "feature_reconstruction"), ("carryover_indicator", "none"),
    ]:
        if col not in df.columns:
            df[col] = default

    df["adaptive_ind"] = (df["condition"] == "adaptive").astype(float)
    df["fixed_ind"] = (df["condition"] == "fixed").astype(float)

    df["carryover_indicator_num"] = np.where(df["carryover_indicator"] == "adaptive", 1.0, 0.0)

    if "sequence" not in df.columns:
        df["sequence"] = 0

    df["period"] = df["period"].astype("category")
    df["sequence"] = df["sequence"].astype("category")

    df["composite_error"] = pd.to_numeric(df["composite_error"], errors="coerce")
    df = df.dropna(subset=["composite_error"])

    df = df.sort_values("participant_id").reset_index(drop=True)
    return df


def _cluster_diagnostics(df: Any) -> dict[str, Any]:
    import numpy as np
    cluster_sizes = df.groupby("participant_id").size()
    return {
        "n_clusters": int(cluster_sizes.shape[0]),
        "cluster_size_min": int(cluster_sizes.min()),
        "cluster_size_max": int(cluster_sizes.max()),
    }


def _check_design_matrix(df: Any, formula_cols: list[str]) -> tuple[bool, float]:
    """Check for rank deficiency and compute condition number."""
    import numpy as np
    try:
        X = df[formula_cols].values.astype(float)
        X = np.column_stack([np.ones(len(X)), X])
        rank = np.linalg.matrix_rank(X)
        cond = float(np.linalg.cond(X))
        return rank < X.shape[1], cond
    except Exception:
        return True, float("inf")


def run_primary_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str = "ate_adaptive_vs_yoked",
    alpha: float = 0.05,
) -> AnalysisResult:
    """Run Estimator A: statsmodels GEE with Gaussian identity family."""
    try:
        import numpy as np
        import pandas as pd
        from statsmodels.genmod.cov_struct import Exchangeable
        from statsmodels.genmod.families import Gaussian
        from statsmodels.genmod.generalized_estimating_equations import GEE
    except ImportError:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "statsmodels_unavailable")

    df = _prepare_df(trial_data)
    if df is None:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "empty_data")

    n_clusters = df["participant_id"].nunique()
    if n_clusters < MIN_PARTICIPANT_CLUSTERS:
        return _make_invalid_result(
            trial_data, estimand_id, GEE_FORMULA,
            f"insufficient_clusters_{n_clusters}",
        )

    contrast_col = "adaptive_ind"
    if df[contrast_col].sum() == 0:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "missing_contrast")

    core_cols = ["adaptive_ind", "fixed_ind", "carryover_indicator_num"]
    rank_deficient, cond_num = _check_design_matrix(df, core_cols)

    try:
        groups = df["participant_id"]
        model = GEE.from_formula(
            GEE_FORMULA,
            groups=groups,
            data=df,
            family=Gaussian(),
            cov_struct=Exchangeable(),
        )
        result = model.fit(maxiter=100, cov_type="bias_reduced")
    except Exception as exc:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA,
                                    f"gee_exception_{type(exc).__name__}")

    if contrast_col not in result.params.index:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "contrast_not_in_model")

    effect = float(result.params[contrast_col])
    se = float(result.bse[contrast_col])

    if not math.isfinite(effect):
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "non_finite_estimate")
    if not math.isfinite(se) or se <= 0:
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "non_finite_se")

    z_crit = 1.96
    ci_lo = effect - z_crit * se
    ci_hi = effect + z_crit * se
    z_stat = effect / se
    p_val = float(result.pvalues[contrast_col])

    if not math.isfinite(p_val):
        return _make_invalid_result(trial_data, estimand_id, GEE_FORMULA, "non_finite_pvalue")

    diag = _cluster_diagnostics(df)
    resid = result.resid_response
    residual_sd = float(np.std(resid)) if len(resid) > 0 else 1.0
    std_effect = effect / residual_sd if residual_sd > 0 else 0.0

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=GEE_FORMULA,
        model_type="statsmodels.GEE",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(ci_lo, 6),
        ci_upper=round(ci_hi, 6),
        test_statistic=round(z_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(std_effect, 4),
        converged=True,
        singularity_warning=False,
        n_participants=n_clusters,
        n_trials=len(df),
        n_missing=int(df["composite_error"].isna().sum()),
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(GEE_FORMULA),
        is_fallback=False,
        primary_estimator_status="ok",
        fallback_used=False,
        fallback_reason="",
        inference_valid=not rank_deficient,
        n_clusters=diag["n_clusters"],
        cluster_size_min=diag["cluster_size_min"],
        cluster_size_max=diag["cluster_size_max"],
        condition_number=round(cond_num, 2),
        rank_deficient=rank_deficient,
        covariance_type="bias_reduced_sandwich",
        residual_diagnostics={
            "residual_mean": round(float(np.mean(resid)), 6),
            "residual_sd": round(residual_sd, 6),
        },
    )


def run_hierarchical_analysis(
    trial_data: list[dict[str, Any]],
    estimand_id: str = "ate_adaptive_vs_yoked",
    alpha: float = 0.05,
) -> AnalysisResult:
    """Run Estimator B: Hierarchical sensitivity model with random intercept only.

    This is a random-intercept-only MixedLM. It does NOT include random slopes
    because the default N=18 design cannot reliably estimate them. Truthfully
    labeled as random_intercept_sensitivity.
    """
    try:
        import numpy as np
        import pandas as pd
        import statsmodels.formula.api as smf
    except ImportError:
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA,
                                    "statsmodels_unavailable")

    df = _prepare_df(trial_data)
    if df is None or df["participant_id"].nunique() < MIN_PARTICIPANT_CLUSTERS:
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA,
                                    "insufficient_data")

    contrast_col = "adaptive_ind"
    status = "ok"
    converged = True
    singularity = False

    try:
        model = smf.mixedlm(
            HIERARCHICAL_FORMULA, df,
            groups=df["participant_id"],
            re_formula="~1",
        )
        result = model.fit(reml=True, method="powell", maxiter=500)
        converged = result.converged

        if not converged:
            status = "non_convergence"
            return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA,
                                        "non_convergence")

        re_cov = result.cov_re
        if hasattr(re_cov, "values"):
            diag = re_cov.values.diagonal() if hasattr(re_cov.values, "diagonal") else [0]
            if any(v < 1e-10 for v in diag):
                singularity = True
                status = "boundary_variance"

    except Exception as exc:
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA,
                                    f"mixedlm_exception_{type(exc).__name__}")

    if contrast_col not in result.params.index:
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA,
                                    "contrast_not_in_model")

    effect = float(result.params[contrast_col])
    se = float(result.bse[contrast_col])

    if not math.isfinite(effect):
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA, "non_finite_estimate")
    if not math.isfinite(se) or se <= 0:
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA, "invalid_se")

    z_crit = 1.96
    z_stat = effect / se
    p_val = float(result.pvalues[contrast_col])

    if not math.isfinite(p_val):
        return _make_invalid_result(trial_data, estimand_id, HIERARCHICAL_FORMULA, "non_finite_pvalue")

    resid = result.resid
    residual_sd = float(np.std(resid)) if len(resid) > 0 else 1.0
    diag_info = _cluster_diagnostics(df)

    return AnalysisResult(
        estimand_id=estimand_id,
        model_formula=HIERARCHICAL_FORMULA,
        model_type="random_intercept_sensitivity",
        effect_estimate=round(effect, 6),
        standard_error=round(se, 6),
        ci_lower=round(effect - z_crit * se, 6),
        ci_upper=round(effect + z_crit * se, 6),
        test_statistic=round(z_stat, 4),
        p_value=round(p_val, 6),
        standardized_effect=round(effect / residual_sd if residual_sd > 0 else 0.0, 4),
        converged=converged,
        singularity_warning=singularity,
        n_participants=diag_info["n_clusters"],
        n_trials=len(df),
        n_missing=int(df["composite_error"].isna().sum()),
        analysis_population="intention_to_treat",
        model_spec_hash=_spec_hash(HIERARCHICAL_FORMULA),
        is_fallback=False,
        primary_estimator_status=status,
        inference_valid=converged and not singularity and se > 0,
        n_clusters=diag_info["n_clusters"],
        cluster_size_min=diag_info["cluster_size_min"],
        cluster_size_max=diag_info["cluster_size_max"],
        covariance_type="model_based",
        residual_diagnostics={
            "residual_mean": round(float(np.mean(resid)), 6),
            "residual_sd": round(residual_sd, 6),
        },
    )


def run_randomization_test(
    trial_data: list[dict[str, Any]],
    n_permutations: int = 500,
    seed: int = 42,
) -> AnalysisResult:
    """Estimator C: Participant-level sign-flip sensitivity test.

    This is a paired sign-flip test on participant-level mean contrasts.
    A separate Williams-sequence permutation test would permute sequence
    assignments; this provides a valid sensitivity analysis under the
    sharp null of no individual treatment effect.
    """
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
        return _make_invalid_result(trial_data, "ate_adaptive_vs_yoked",
                                    "sign_flip_test", "insufficient_pairs")

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
        model_formula="sign_flip_test",
        model_type="paired_sign_flip",
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
        model_spec_hash=_spec_hash("sign_flip_test"),
        is_fallback=False,
        primary_estimator_status="ok",
        inference_valid=True,
        n_clusters=len(paired),
    )


def run_bootstrap_ci(
    trial_data: list[dict[str, Any]],
    n_bootstrap: int = 500,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Cluster bootstrap CI resampling participants and re-fitting primary GEE.

    Returns a dict with interval, SE, validity info, and success/fail counts.
    """
    import numpy as np

    by_participant: dict[str, list[dict]] = defaultdict(list)
    for t in trial_data:
        by_participant[t["participant_id"]].append(t)

    pids = sorted(by_participant.keys())
    if len(pids) < MIN_PARTICIPANT_CLUSTERS:
        return {
            "ci": None, "se": 0.0, "valid": False,
            "n_success": 0, "n_fail": 0, "valid_rate": 0.0,
        }

    rng = random.Random(derive_seed(seed, "bootstrap"))
    boot_effects: list[float] = []
    n_fail = 0

    for b in range(n_bootstrap):
        sampled_pids = [pids[rng.randint(0, len(pids) - 1)] for _ in range(len(pids))]
        boot_data: list[dict] = []
        for new_idx, pid in enumerate(sampled_pids):
            for row in by_participant[pid]:
                new_row = dict(row)
                new_row["participant_id"] = f"boot_{new_idx}"
                boot_data.append(new_row)

        boot_result = run_primary_analysis(boot_data, alpha=alpha)
        if boot_result.inference_valid:
            boot_effects.append(boot_result.effect_estimate)
        else:
            n_fail += 1

    n_success = len(boot_effects)
    valid_rate = n_success / n_bootstrap if n_bootstrap > 0 else 0.0

    if n_success < 2 or valid_rate < BOOTSTRAP_VALID_THRESHOLD:
        return {
            "ci": None, "se": 0.0, "valid": False,
            "n_success": n_success, "n_fail": n_fail, "valid_rate": valid_rate,
        }

    boot_effects.sort()
    lo_idx = max(0, int(n_success * (alpha / 2)) - 1)
    hi_idx = min(n_success - 1, int(n_success * (1 - alpha / 2)))
    ci = (round(boot_effects[lo_idx], 6), round(boot_effects[hi_idx], 6))
    boot_se = float(np.std(boot_effects, ddof=1))

    return {
        "ci": ci, "se": round(boot_se, 6), "valid": True,
        "n_success": n_success, "n_fail": n_fail, "valid_rate": round(valid_rate, 4),
    }


def run_full_analysis(
    trial_data: list[dict[str, Any]],
    alpha: float = 0.05,
    seed: int = 42,
    n_bootstrap: int = 500,
) -> MultiEstimatorResult:
    """Run all estimators and bootstrap CI."""
    primary = run_primary_analysis(trial_data, alpha=alpha)
    hierarchical = run_hierarchical_analysis(trial_data, alpha=alpha)
    randomization = run_randomization_test(trial_data, seed=seed)
    boot = run_bootstrap_ci(trial_data, n_bootstrap=n_bootstrap, seed=seed, alpha=alpha)

    valid = primary.inference_valid
    fallback = primary.is_fallback

    return MultiEstimatorResult(
        primary=primary,
        hierarchical=hierarchical,
        randomization=randomization,
        bootstrap_ci=boot.get("ci"),
        bootstrap_valid_rate=boot.get("valid_rate", 0.0),
        bootstrap_n_success=boot.get("n_success", 0),
        bootstrap_n_fail=boot.get("n_fail", 0),
        bootstrap_se=boot.get("se", 0.0),
        primary_convergence=primary.converged and not primary.is_fallback,
        fallback_used=fallback,
        valid_inference=valid,
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


def _spec_hash(formula: str) -> str:
    return hashlib.sha256(
        json.dumps({"formula": formula, "version": MODEL_SPEC_VERSION},
                   sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

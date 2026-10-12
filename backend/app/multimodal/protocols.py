"""Experimental protocols A-G: specifications and runners.

Runners operate on whatever data they are given and stamp results with source kinds. Without real recordings,
A-D run on SYNTHETIC data to demonstrate the pipeline; E-G run as design simulations whose purpose is to check
type-I error and power of the planned analysis, not to estimate any human effect.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from app.multimodal.acquisition.synthetic_signals import synth_eeg_epochs
from app.multimodal.evaluation import SYNTHETIC_DISCLAIMER, cross_validate, hedges_g, holm
from app.multimodal.fusion import ablation, synthetic_fusion_dataset
from app.multimodal.processing.eeg_decoding import make_fbcsp_lda, make_tangent_lr

PROTOCOLS = {
    "A": {"name": "Perception vs imagery vs rest", "unit": "trial", "split": "subject-grouped (LOSO)",
          "primary": "balanced accuracy vs permutation null", "controls": ["label permutation", "ocular-only model"]},
    "B": {"name": "High vs low self-reported vividness", "unit": "trial",
          "split": "within-subject median split, LOSO evaluation",
          "primary": "AUC vs permutation null", "controls": ["effort/arousal-only model", "permutation"]},
    "C": {"name": "Subject-specific vs cross-subject decoding", "unit": "subject",
          "split": "within-subject k-fold vs LOSO on identical data", "primary": "paired accuracy difference",
          "controls": ["permutation"]},
    "D": {"name": "Unimodal vs multimodal estimation", "unit": "subject", "split": "LOSO",
          "primary": "fusion minus best unimodal accuracy", "controls": ["leave-one-modality-out ablation"]},
    "E": {"name": "Neurofeedback vs sham feedback", "unit": "participant",
          "design": "randomized, participant-blind, yoked sham",
          "primary": "change in cue-free probe vividness", "controls": ["yoked sham", "blinding check"]},
    "F": {"name": "Feedback vs no-feedback imagery training", "unit": "participant", "design": "randomized",
          "primary": "change in cue-free probe vividness and objective rotation accuracy",
          "controls": ["no-feedback arm", "expectancy rating"]},
    "G": {"name": "Longitudinal transfer and persistence", "unit": "participant", "design": "repeated sessions",
          "primary": "slope of cue-free probe outcomes; follow-up retention",
          "controls": ["no-feedback arm", "practice-only arm"]},
}
CAUSAL_PROTOCOLS = {"E", "F", "G"}


def _wrap(protocol: str, result: dict, source_kinds: list[str]) -> dict:
    synthetic = "REAL_SENSOR" not in source_kinds
    return {"protocol": protocol, "spec": PROTOCOLS[protocol], "source_kinds": source_kinds,
            "scope": SYNTHETIC_DISCLAIMER if synthetic else "Real data: confirmatory claims need preregistration.",
            "result": result}


def run_protocol_a(x=None, y=None, groups=None, fs: float = 128.0, source_kinds=("SYNTHETIC",), seed: int = 0,
                   n_permutations: int = 19) -> dict:
    if x is None:
        x, y, groups = synth_eeg_epochs(n_subjects=5, n_trials_per_class=30, seed=seed)
    res = cross_validate(lambda: make_fbcsp_lda(fs), x, y, groups, "loso", list(source_kinds), "fbcsp_lda",
                         n_permutations=n_permutations, seed=seed)
    return _wrap("A", res.to_dict(), list(source_kinds))


def run_protocol_b(features=None, vividness=None, groups=None, source_kinds=("SYNTHETIC",), seed: int = 0) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)
    if features is None:
        n_sub, n_tr = 8, 40
        groups = np.repeat(np.arange(n_sub), n_tr)
        vividness = rng.uniform(0, 1, n_sub * n_tr)
        features = rng.normal(0, 1, (n_sub * n_tr, 6))
        features[:, 0] += 0.8 * (vividness - 0.5) + rng.normal(0, 0.3, n_sub)[groups]
    labels = np.zeros_like(vividness, dtype=int)
    for g in np.unique(groups):
        m = groups == g
        labels[m] = (vividness[m] > np.median(vividness[m])).astype(int)
    aucs = []
    for g in np.unique(groups):
        tr, te = groups != g, groups == g
        clf = LogisticRegression(max_iter=1000).fit(features[tr], labels[tr])
        aucs.append(roc_auc_score(labels[te], clf.predict_proba(features[te])[:, 1]))
    null = []
    for _ in range(50):
        lp = labels.copy()
        for g in np.unique(groups):
            m = np.where(groups == g)[0]
            lp[m] = rng.permutation(lp[m])
        s = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            clf = LogisticRegression(max_iter=1000).fit(features[tr], lp[tr])
            s.append(roc_auc_score(lp[te], clf.predict_proba(features[te])[:, 1]))
        null.append(np.mean(s))
    obs = float(np.mean(aucs))
    p = (1 + int(np.sum(np.array(null) >= obs))) / 51
    return _wrap("B", {"auc_loso": obs, "fold_auc": aucs, "permutation_p": p,
                       "label_definition": "within-subject median split of self-reported vividness"},
                 list(source_kinds))


def run_protocol_c(x=None, y=None, groups=None, source_kinds=("SYNTHETIC",), seed: int = 0) -> dict:
    if x is None:
        x, y, groups = synth_eeg_epochs(n_subjects=5, n_trials_per_class=30, seed=seed)
    within = cross_validate(make_tangent_lr, x, y, groups, "within_subject", list(source_kinds), "ts_within")
    loso = cross_validate(make_tangent_lr, x, y, groups, "loso", list(source_kinds), "ts_loso")
    return _wrap("C", {"within_subject": within.to_dict(), "loso": loso.to_dict(),
                       "difference": within.mean - loso.mean,
                       "note": "Cross-subject loss reflects inter-subject variability not handled by this baseline."},
                 list(source_kinds))


def run_protocol_d(ds=None, seed: int = 0) -> dict:
    ds = ds or synthetic_fusion_dataset(n_subjects=6, n_trials=50, seed=seed)
    res = ablation(ds, "late")
    return _wrap("D", res, ds.source_kinds)


def simulate_two_arm(n_per_arm: int, true_effect: float, seed: int, n_sessions: int = 6,
                     sd_between: float = 0.15, sd_within: float = 0.1) -> dict:
    """Design simulation for E/F/G: per-participant probe outcomes across sessions in two arms."""
    rng = np.random.default_rng(seed)
    out = {}
    for arm, eff in (("active", true_effect), ("control", 0.0)):
        base = rng.normal(0.45, sd_between, n_per_arm)
        slope_p = rng.normal(0.01 + eff / max(n_sessions - 1, 1), 0.01, n_per_arm)
        sess = np.arange(n_sessions)
        y = base[:, None] + slope_p[:, None] * sess[None] + rng.normal(0, sd_within, (n_per_arm, n_sessions))
        out[arm] = y
    return out


def analyze_two_arm(sim: dict, n_boot: int = 1000, seed: int = 0) -> dict:
    da = sim["active"][:, -1] - sim["active"][:, 0]
    dc = sim["control"][:, -1] - sim["control"][:, 0]
    t, p = stats.ttest_ind(da, dc, equal_var=False)
    rng = np.random.default_rng(seed)
    boots = [rng.choice(da, da.size).mean() - rng.choice(dc, dc.size).mean() for _ in range(n_boot)]
    sess = np.arange(sim["active"].shape[1])
    slope = lambda y: np.polyfit(sess, y.T, 1)[0]  # noqa: E731
    _, p_slope = stats.ttest_ind(slope(sim["active"]), slope(sim["control"]), equal_var=False)
    return {"mean_change_diff": float(da.mean() - dc.mean()), "welch_t": float(t), "p_change": float(p),
            "p_slope": float(p_slope), "hedges_g": hedges_g(da, dc),
            "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "holm": holm({"change": float(p), "slope": float(p_slope)})}


def design_operating_characteristics(n_per_arm: int = 20, effects=(0.0, 0.1), n_sims: int = 400,
                                     seed: int = 0) -> dict:
    out = {}
    for eff in effects:
        rej = [analyze_two_arm(simulate_two_arm(n_per_arm, eff, seed + i), n_boot=1)["p_change"] < 0.05
               for i in range(n_sims)]
        out[f"effect_{eff}"] = {"rejection_rate": float(np.mean(rej)), "n_sims": n_sims}
    return {"n_per_arm": n_per_arm, "results": out,
            "interpretation": "effect_0.0 estimates type-I error; non-zero effects estimate power. "
                              "Simulated outcomes only."}


def run_protocol_causal(protocol: str, n_per_arm: int = 20, true_effect: float = 0.0, seed: int = 0) -> dict:
    if protocol not in CAUSAL_PROTOCOLS:
        raise ValueError(f"{protocol} is not a causal/longitudinal protocol")
    sim = simulate_two_arm(n_per_arm, true_effect, seed)
    return _wrap(protocol, {"design_simulation": True, "simulated_true_effect": true_effect,
                            "analysis": analyze_two_arm(sim, seed=seed),
                            "operating_characteristics": design_operating_characteristics(n_per_arm, n_sims=200,
                                                                                          seed=seed)},
                 ["SYNTHETIC"])

"""ANIMUS-P2 per-subject decoding pipeline (the sealed method, shared by validation + confirmatory).

`evaluate_subject_arrays` runs the frozen pipeline on one subject's arrays: grouped-by-identity split,
leakage + fold-safe normalization, nested-validation ridge with bootstrap-ensemble uncertainty + reject,
content margin M with permutation + identity bootstrap + multi-seed, 2AFC, retrieval, category-matched and
low-level controls, and the subject PASS. Both the synthetic method validation and the REAL confirmatory
call this identical function so the confirmatory cannot diverge from what was sealed.
"""
from __future__ import annotations

import numpy as np

from app.core.animus.p2 import metrics as M
from app.core.animus.p2.decoder import BootstrapEnsembleDecoder, select_alpha
from app.core.animus.p2.features import FoldSafeNormalizer, leakage_test_normalizer
from app.core.animus.p2.gate import subject_pass
from app.core.animus.p2.splits import (
    assert_no_identity_leakage,
    freeze_identity_split,
    perceptual_hash_audit,
    trial_partition,
)
from app.core.animus.p2.synthetic import unique_gallery


def evaluate_subject_arrays(subject: str, X, stimulus_ids, Y, categories=None, low_level=None,
                            atlas_qc_pass: bool = True, n_perm: int = 1000, n_boot: int = 1000,
                            n_components: int | None = None, split_seed: int = 20260909,
                            reject_quantile: float = 0.9) -> dict:
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    stimulus_ids = [str(s) for s in stimulus_ids]

    split = freeze_identity_split(stimulus_ids, seed=split_seed)
    leak = assert_no_identity_leakage(stimulus_ids, split)
    fam = perceptual_hash_audit(Y, stimulus_ids, split)
    part = trial_partition(stimulus_ids, split)
    tr, va, te = part == "train", part == "val", part == "test"

    norm = FoldSafeNormalizer(n_components=n_components).fit(X[tr])
    Xtr, Xva, Xte = norm.transform(X[tr]), norm.transform(X[va]), norm.transform(X[te])
    leak_norm = leakage_test_normalizer(X[tr], X[te])

    alpha, alpha_scores = select_alpha(Xtr, Y[tr], Xva, Y[va])
    ens = BootstrapEnsembleDecoder(alpha=alpha, n_boot=20).fit(Xtr, Y[tr])
    ens.calibrate_reject(Xva, reject_quantile)
    pred, unc = ens.predict_with_uncertainty(Xte)
    true = Y[te]

    margin = M.content_margin(pred, true)
    perm_p = M.permutation_p(pred, true, n_perm=n_perm)
    ci = M.identity_bootstrap_ci(pred, true, n_boot=n_boot)
    seeds = M.multi_seed_margin(pred, true)
    afc = M.two_afc(pred, true)

    gal, gal_ids = unique_gallery(Y, stimulus_ids, split["test"])
    te_ids = [s for s, m in zip(stimulus_ids, te) if m]
    pred_by_id: dict = {}
    for p, s in zip(pred, te_ids):
        pred_by_id.setdefault(s, []).append(p)
    q = np.stack([np.mean(pred_by_id[i], 0) for i in gal_ids])
    retr = M.retrieval(q, gal)

    catm = None
    if categories is not None:
        catm = M.category_matched_2afc(pred, true, [c for c, m in zip(categories, te) if m])
    ll_margin = None
    if low_level is not None:
        low_level = np.asarray(low_level, float)
        ll_margin = M.low_level_baseline_margin(low_level[te], true, low_level[tr], Y[tr])

    true_sim = np.sum(M.unit_l2(pred) * M.unit_l2(true), axis=1)
    calib_rho = float(np.corrcoef(np.argsort(np.argsort(unc)),
                                  np.argsort(np.argsort(-true_sim)))[0, 1])
    reject_frac = float(np.mean(~ens.valid_mask(unc)))

    res = {
        "subject": subject,
        "data_contract_pass": bool(leak["leakage_free"] and leak_norm["pass"] and fam["family_leakage_free"]),
        "atlas_qc_pass": bool(atlas_qc_pass),
        "leakage": leak, "family_audit": fam, "normalizer_leakage_test": leak_norm,
        "alpha": alpha, "alpha_scores": alpha_scores,
        "margin_M": round(float(margin), 5), "permutation_p": round(float(perm_p), 5),
        "bootstrap_ci95": [round(ci[0], 5), round(ci[1], 5)], "bootstrap_ci_lower": round(ci[0], 5),
        "all_seeds_positive": seeds["all_positive"], "per_seed": seeds["per_seed_margin"],
        "two_afc": afc, "retrieval": retr, "category_matched_2afc": catm,
        "low_level_baseline_margin": None if ll_margin is None else round(float(ll_margin), 5),
        "neural_beats_low_level": None if ll_margin is None else bool(margin > ll_margin),
        "uncertainty_error_rank_corr": round(calib_rho, 4), "reject_fraction": round(reject_frac, 4),
        "n_test_trials": int(te.sum()), "n_test_identities": len(gal_ids),
        "n_train_identities": split["n_train"], "n_voxels": int(X.shape[1]),
    }
    res["pass"] = bool(subject_pass(res))
    return res

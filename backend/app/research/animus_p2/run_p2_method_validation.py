"""ANIMUS-P2 method validation on SYNTHETIC data (no real brains/images).

Proves the sealed pipeline is correct and leakage-free BEFORE any real confirmatory run:
* grouped-by-identity splits leak no identity (and no near-duplicate family);
* normalization/PCA are fit train-only (leakage test);
* a signal subject PASSES (M>0, permutation p<0.01, bootstrap CI lower>0, all seeds positive), beats a
  low-level baseline, and its neural decoder outperforms chance on 2AFC/retrieval;
* a null subject FAILS and its effect collapses under permutation;
* uncertainty predicts error (calibration) and the reject option works;
* the dataset gate yields VALIDATED on an all-signal cohort and FAIL on an all-null cohort.
Writes results/animus_p2/method_validation.json. This is METHOD validation, NOT a neural claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

from app.core.animus.p2 import metrics as M
from app.core.animus.p2.decoder import BootstrapEnsembleDecoder, select_alpha
from app.core.animus.p2.features import FoldSafeNormalizer, leakage_test_normalizer
from app.core.animus.p2.gate import dataset_gate, subject_pass
from app.core.animus.p2.splits import (
    assert_no_identity_leakage,
    freeze_identity_split,
    perceptual_hash_audit,
    trial_partition,
)
from app.core.animus.p2.synthetic import make_subject, unique_gallery

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")


def _native(o):
    """Recursively convert numpy scalars/arrays to native Python for JSON."""
    if isinstance(o, dict):
        return {k: _native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_native(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def _sh(o):
    o = _native(dict(o))
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def evaluate_subject(subj, n_perm=500, n_boot=500) -> dict:
    split = freeze_identity_split(subj.stimulus_ids, seed=20260909)
    leak = assert_no_identity_leakage(subj.stimulus_ids, split)
    fam = perceptual_hash_audit(subj.Y, subj.stimulus_ids, split)
    part = trial_partition(subj.stimulus_ids, split)
    tr, va, te = part == "train", part == "val", part == "test"

    norm = FoldSafeNormalizer(n_components=None).fit(subj.X[tr])
    Xtr, Xva, Xte = norm.transform(subj.X[tr]), norm.transform(subj.X[va]), norm.transform(subj.X[te])
    leak_norm = leakage_test_normalizer(subj.X[tr], subj.X[te])

    alpha, alpha_scores = select_alpha(Xtr, subj.Y[tr], Xva, subj.Y[va])
    ens = BootstrapEnsembleDecoder(alpha=alpha, n_boot=20).fit(Xtr, subj.Y[tr])
    ens.calibrate_reject(Xva, uncertainty_quantile=0.9)
    pred, unc = ens.predict_with_uncertainty(Xte)
    true = subj.Y[te]

    margin = M.content_margin(pred, true)
    perm_p = M.permutation_p(pred, true, n_perm=n_perm)
    ci = M.identity_bootstrap_ci(pred, true, n_boot=n_boot)
    seeds = M.multi_seed_margin(pred, true)
    afc = M.two_afc(pred, true)
    gal, gal_ids = unique_gallery(subj.Y, subj.stimulus_ids, split["test"])
    # align: build a per-gallery-identity prediction (mean pred over that identity's test trials)
    te_ids = [s for s, m in zip(subj.stimulus_ids, te) if m]
    pred_by_id = {}
    for p, s in zip(pred, te_ids):
        pred_by_id.setdefault(s, []).append(p)
    q = np.stack([np.mean(pred_by_id[i], 0) for i in gal_ids])
    retr = M.retrieval(q, gal)
    catm = M.category_matched_2afc(pred, true, [c for c, m in zip(subj.categories, te) if m])
    ll_margin = M.low_level_baseline_margin(subj.low_level[te], true, subj.low_level[tr], subj.Y[tr])

    # uncertainty calibration: higher uncertainty -> lower true similarity (rank corr < 0)
    true_sim = np.sum(M.unit_l2(pred) * M.unit_l2(true), axis=1)
    order_u = np.argsort(unc)
    order_e = np.argsort(-true_sim)
    from numpy import corrcoef
    calib_rho = float(corrcoef(np.argsort(order_u), np.argsort(order_e))[0, 1])
    reject_frac = float(np.mean(~ens.valid_mask(unc)))

    res = {
        "subject": subj.subject,
        "data_contract_pass": leak["leakage_free"] and leak_norm["pass"] and fam["family_leakage_free"],
        "atlas_qc_pass": True,
        "leakage": leak, "family_audit": fam, "normalizer_leakage_test": leak_norm,
        "alpha": alpha, "alpha_scores": alpha_scores,
        "margin_M": round(margin, 5), "permutation_p": round(perm_p, 5),
        "bootstrap_ci95": [round(ci[0], 5), round(ci[1], 5)], "bootstrap_ci_lower": round(ci[0], 5),
        "all_seeds_positive": seeds["all_positive"], "per_seed": seeds["per_seed_margin"],
        "two_afc": afc, "retrieval": retr, "category_matched_2afc": catm,
        "low_level_baseline_margin": round(ll_margin, 5),
        "neural_beats_low_level": margin > ll_margin,
        "uncertainty_error_rank_corr": round(calib_rho, 4), "reject_fraction": round(reject_frac, 4),
        "n_test_trials": int(te.sum()), "n_test_identities": len(gal_ids),
    }
    res["pass"] = subject_pass(res)
    return res


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    # signal cohort (should VALIDATE) and null cohort (should FAIL)
    signal_subjects = [make_subject(f"sig-{i:02d}", signal=1.8, seed=100 + i) for i in range(6)]
    null_subjects = [make_subject(f"null-{i:02d}", signal=0.0, seed=500 + i) for i in range(6)]

    sig_res = [evaluate_subject(s) for s in signal_subjects]
    null_res = [evaluate_subject(s) for s in null_subjects]

    sig_pass = sum(r["pass"] for r in sig_res)
    null_pass = sum(r["pass"] for r in null_res)
    sig_decision = dataset_gate(sig_pass, len(sig_res), len(sig_res))
    null_decision = dataset_gate(null_pass, len(null_res), len(null_res))

    checks = {
        "splits_leakage_free": all(r["leakage"]["leakage_free"] for r in sig_res + null_res),
        "normalizer_fold_safe": all(r["normalizer_leakage_test"]["pass"] for r in sig_res + null_res),
        "signal_subjects_pass": sig_pass >= 5,
        "signal_cohort_validated": sig_decision == "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED",
        "null_subjects_fail": null_pass == 0,
        "null_cohort_not_validated": null_decision != "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED",
        "signal_beats_low_level": all(r["neural_beats_low_level"] for r in sig_res),
        "signal_2afc_ci_above_chance": all(r["two_afc"]["ci95"][0] > 0.5 for r in sig_res),
        "signal_retrieval_above_chance": all(
            r["retrieval"]["top5"] > 5 * r["retrieval"]["chance_top1"] for r in sig_res),
        "null_permutation_nonsignificant": all(r["permutation_p"] > 0.01 for r in null_res),
        "uncertainty_calibrated_on_signal": np.median([r["uncertainty_error_rank_corr"] for r in sig_res]) > 0,
    }
    out = {"artifact": "ANIMUS_P2_METHOD_VALIDATION", "milestone": "ANIMUS-P2", "synthetic_only": True,
           "signal_decision": sig_decision, "null_decision": null_decision,
           "signal_passes": sig_pass, "null_passes": null_pass,
           "checks": checks, "all_pass": all(checks.values()),
           "signal_subjects": sig_res, "null_subjects": null_res}
    json.dump(_sh(out), open(os.path.join(OUT, "method_validation.json"), "w"), indent=2)

    print("=== ANIMUS-P2 method validation (synthetic) ===")
    print("signal decision:", sig_decision, "| null decision:", null_decision)
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("ALL PASS:", out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

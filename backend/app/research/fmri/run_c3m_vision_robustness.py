"""C3M vision-gate ROBUSTNESS battery (Set B primary, VISION ONLY, sealed).

Before the primary vision gate can be declared PASS (and before any imagery
unblinding), M3 CORAL must survive:

1. CAPACITY-MATCHED control at M3's TRUE capacity. M3 = whiten session cov
   (rank r_s) + recolor onto the top-K perception PCs. The earlier matched-random
   (rank-39 session-orthogonal) under-matches the rank-K recolor. Here the control
   keeps M3's exact structure but inserts a random orthogonal rotation Q (KxK)
   on the perception-subspace coefficients before recolor: identical capacity
   (rank r_s whiten + rank-K perception-subspace map), random orientation. >=200
   draws; M3 must exceed the 95th percentile of their held-out Set B MRR.

2. VISION-ONLY hyperparameter sensitivity: grid over CORAL shrinkage and
   perception rank; report held-out Set B MRR, dominant_fraction, and the exact
   6! permutation p for each. Robustness (not cherry-picking) requires the PASS
   to hold across a broad range; the frozen setting is committed a priori.

All choices use held-out VISION performance only. No imagery row is loaded.
Writes results/c3m_vision_robustness.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import time
from pathlib import Path

import numpy as np

from app.research.fmri import cross_session_alignment as csa
from app.research.fmri.decoder import TrainedDecoder  # noqa: F401
from app.research.fmri.nsdimagery_transfer import extract_imagery_rows
from app.research.fmri.run_c3m_vision_gate import (
    within_set_metrics, _collapse_from_predictions, exact_permutation_null_mrr,
)
from app.research.fmri.run_c3m_vision_gate_m3m4 import (
    precompute_perception_coral, build_coral_transform,
)

SEED = 20260822
N_CAP = 200


def build_coral_random_rotation(S, mu_p, Up, sqrt_ep, shrinkage, seed, eps=1e-8):
    """M3-capacity control: same whiten+recolor, but a random orthogonal rotation
    Q (KxK) scrambles the perception-subspace coordinate<->eigenvalue pairing."""
    S = np.asarray(S, dtype=np.float64)
    m_s = S.mean(axis=0)
    Us, es = csa._shrunk_cov(S - m_s, shrinkage)
    inv_sqrt_s = 1.0 / np.sqrt(np.clip(es, eps, None))
    rng = np.random.default_rng(seed)
    G = rng.standard_normal((Up.shape[1], Up.shape[1]))
    Q, _ = np.linalg.qr(G)
    mu_p = np.asarray(mu_p, dtype=np.float64)

    def apply(X):
        Xc = np.asarray(X, dtype=np.float64)
        if Xc.ndim == 1:
            Xc = Xc[None, :]
        Xc = Xc - m_s
        coeff_s = Xc @ Us
        z = (coeff_s * inv_sqrt_s) @ Us.T + (Xc - coeff_s @ Us.T)
        coeff_p = (z @ Up) @ Q            # random rotation within perception subspace
        out = (coeff_p * sqrt_ep) @ Up.T + (z - (z @ Up) @ Up.T)
        return out + mu_p

    return apply


def loto_m3(X, targets, decoder, mu_p, Up, sqrt_ep, shrinkage, rot_seed=None):
    uniq = list(dict.fromkeys(targets.tolist()))
    preds = np.empty((X.shape[0], decoder.weights.shape[1]), dtype=np.float64)
    for t in uniq:
        te = targets == t
        S = X[~te]
        if rot_seed is None:
            T = build_coral_transform(S, mu_p, Up, sqrt_ep, shrinkage)
            preds[te] = decoder.predict(T(X[te]))
        else:
            ap = build_coral_random_rotation(S, mu_p, Up, sqrt_ep, shrinkage, rot_seed)
            preds[te] = decoder.predict(ap(X[te]))
    return preds


def main():
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    decoder_path = Path(os.environ["C3M_DECODER"])
    pool_path = Path(os.environ["C3M_POOL"])
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])
    xp_dir = Path(os.environ["XP_DIR"])
    frozen_shrink = float(os.environ.get("CORAL_SHRINKAGE", "0.1"))
    frozen_rank = int(os.environ.get("CORAL_PERCEPTION_RANK", "400"))
    xp_sub = int(os.environ.get("XP_SUBSAMPLE", "2500"))

    frozen = pickle.load(open(decoder_path, "rb"))
    decoder = frozen["decoder"]
    beta_coords = np.asarray(frozen["beta_coords"])
    mu_p = np.asarray(decoder.voxel_mean, dtype=np.float64)
    pool = np.load(pool_path).astype(np.float64)
    rows = json.load(open(manifest_path))["rows"]

    setB = [r for r in rows if r["event_type"] == "vision" and r["stimulus_set"] == "B"]
    idxr = [r["beta_row_index"] for r in setB]
    XB = extract_imagery_rows(imagery_betas, beta_coords, idxr).astype(np.float64)
    tB = np.array([r["candidate_pool_index"] for r in setB])
    cols = sorted(set(int(x) for x in tB))

    sess_files = sorted(f for f in xp_dir.glob("xp_*_session*.npy") if "nsdid" not in f.name)
    P_all = np.concatenate([np.load(f).astype(np.float64) for f in sess_files], axis=0)
    rng = np.random.default_rng(SEED)
    P = P_all[np.sort(rng.choice(P_all.shape[0], size=min(xp_sub, P_all.shape[0]), replace=False))]

    def eval_preds(preds):
        m = within_set_metrics(preds, pool, cols, tB)
        c = _collapse_from_predictions(preds, pool, cols)
        p = exact_permutation_null_mrr(preds, pool, cols, tB)
        return {"mrr": m["mrr"], "two_afc": m["two_afc"],
                "dominant_fraction": c["dominant_fraction"], "degenerate": c["degenerate"],
                "perm_p": p["p_value"], "pred_cov_effective_rank": m["pred_cov_effective_rank"]}

    # ---- frozen-setting M3 (true) ----
    _, Up, sqrt_ep = precompute_perception_coral(P, frozen_shrink, frozen_rank)
    m3_true = eval_preds(loto_m3(XB, tB, decoder, mu_p, Up, sqrt_ep, frozen_shrink))

    # ---- capacity-matched control (random rotation within perception subspace) ----
    rng2 = np.random.default_rng(SEED)
    cap_mrr, cap_dom = [], []
    for _ in range(N_CAP):
        s = int(rng2.integers(0, 2**31 - 1))
        preds = loto_m3(XB, tB, decoder, mu_p, Up, sqrt_ep, frozen_shrink, rot_seed=s)
        m = within_set_metrics(preds, pool, cols, tB)
        c = _collapse_from_predictions(preds, pool, cols)
        cap_mrr.append(m["mrr"]); cap_dom.append(c["dominant_fraction"])
    cap_mrr = np.asarray(cap_mrr); cap_dom = np.asarray(cap_dom)
    capacity_control = {
        "n": N_CAP, "control": "random_orthogonal_rotation_within_rank%d_perception_subspace" % frozen_rank,
        "control_mrr_mean": float(cap_mrr.mean()), "control_mrr_95pct": float(np.percentile(cap_mrr, 95)),
        "control_mrr_max": float(cap_mrr.max()),
        "control_dominant_fraction_mean": float(cap_dom.mean()),
        "m3_true_mrr": m3_true["mrr"],
        "m3_exceeds_control_95pct": bool(m3_true["mrr"] > np.percentile(cap_mrr, 95)),
        "m3_exceeds_control_max": bool(m3_true["mrr"] > cap_mrr.max()),
    }

    # ---- vision-only hyperparameter sensitivity ----
    # one perception SVD (max rank), derive every (shrinkage, rank) from it
    mu_P = P.mean(axis=0)
    _, s_full, Vt_full = np.linalg.svd(P - mu_P, full_matrices=False)
    npc = P.shape[0]
    ev_full = (s_full ** 2) / max(npc - 1, 1)
    ev_mean = float(np.mean(ev_full))
    grid = []
    for sh in [0.05, 0.1, 0.2, 0.5]:
        for rk in [100, 200, 400, 800]:
            k = int(min(rk, Vt_full.shape[0]))
            Upg = Vt_full[:k].T
            shr = (1.0 - sh) * ev_full[:k] + sh * ev_mean
            seg = np.sqrt(np.clip(shr, 1e-8, None))
            res = eval_preds(loto_m3(XB, tB, decoder, mu_p, Upg, seg, sh))
            res.update({"shrinkage": sh, "perception_rank": rk})
            grid.append(res)

    n_pass = sum(1 for g in grid if g["mrr"] > 0.408 and not g["degenerate"]
                 and g["two_afc"] > 0.5 and g["perm_p"] < 0.05)

    out = {
        "artifact": "C3M_VISION_ROBUSTNESS",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal": "VISION_SET_B_ONLY_NO_IMAGERY_LOADED",
        "frozen_setting": {"shrinkage": frozen_shrink, "perception_rank": frozen_rank,
                           "xp_subsample": xp_sub},
        "m3_frozen": m3_true,
        "capacity_matched_control": capacity_control,
        "hyperparameter_sensitivity": grid,
        "sensitivity_summary": {"n_settings": len(grid), "n_pass_all_guards": n_pass,
                                "fraction_pass": n_pass / len(grid)},
        "provenance": {"frozen_decoder_weights_hash": frozen["weights_hash"],
                       "imagery_betas_sha256": hashlib.sha256(open(imagery_betas, "rb").read()).hexdigest()
                       if imagery_betas.stat().st_size < (1 << 30) else "SKIP_LARGE"},
    }
    out["self_hash"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(out, open(results_dir / "c3m_vision_robustness.json", "w"), indent=2)
    print(f"Wrote {results_dir}/c3m_vision_robustness.json\n")
    print("M3 frozen:", {k: round(v, 4) if isinstance(v, float) else v for k, v in m3_true.items()})
    print("Capacity control:", json.dumps(capacity_control, indent=1))
    print(f"\nSensitivity: {n_pass}/{len(grid)} settings pass ALL guards")
    for g in grid:
        print(f"  shrink={g['shrinkage']:.2f} rank={g['perception_rank']:4d} "
              f"MRR={g['mrr']:.3f} domfrac={g['dominant_fraction']:.3f} "
              f"2AFC={g['two_afc']:.3f} p={g['perm_p']:.4f} "
              f"{'PASS' if (g['mrr']>0.408 and not g['degenerate'] and g['two_afc']>0.5 and g['perm_p']<0.05) else 'fail'}")


if __name__ == "__main__":
    main()

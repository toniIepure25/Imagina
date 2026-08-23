"""C3M vision gate, Family-A covariance/distribution methods M3 (CORAL) and
M4 (low-rank moment), which require the core-NSD perception reference X_p.

Same sealed, held-out-target LOTO protocol and metric suite as
run_c3m_vision_gate.py (M0-M2); adds M3/M4 and re-reports M0 as the in-run
baseline. X_p is a deterministic subsample of the rolling-extracted perception
betas (betas_fithrf, decoder voxel order), used TARGET-BLIND (only its
distribution/covariance, never any imagery/vision target identity).

Writes results/c3m_vision_gate_m3m4.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import numpy as np

from app.research.fmri import cross_session_alignment as csa
from app.research.fmri.decoder import TrainedDecoder  # noqa: F401 (unpickle)
from app.research.fmri.nsdimagery_transfer import extract_imagery_rows
from app.research.fmri.run_c3m_vision_gate import (
    within_set_metrics, _collapse_from_predictions, exact_permutation_null_mrr,
)

SEED = 20260822
N_MATCHED_RANDOM = 200
XP_SUBSAMPLE = 2500
CORAL_SHRINKAGE = 0.1
CORAL_PERCEPTION_RANK = 400   # top-K perception PCs for the CORAL recolor
M4_RANK = 20


def precompute_perception_coral(P, shrinkage, rank, eps=1e-8):
    """Perception recolor factors for CORAL, computed ONCE (fold-independent).
    Returns (mu_P, Up [V,K], sqrt_shr_evals [K])."""
    mu_P = P.mean(axis=0)
    Pc = P - mu_P
    _, s, Vt = np.linalg.svd(Pc, full_matrices=False)
    k = int(min(rank, Vt.shape[0]))
    Up = Vt[:k].T
    evals = (s[:k] ** 2) / max(Pc.shape[0] - 1, 1)
    mu = float(np.mean((s ** 2) / max(Pc.shape[0] - 1, 1)))
    shr = (1.0 - shrinkage) * evals + shrinkage * mu
    return mu_P, Up, np.sqrt(np.clip(shr, eps, None))


def build_coral_transform(S, mu_p, Up, sqrt_ep, shrinkage, eps=1e-8):
    """CORAL transform with the perception recolor precomputed; only the (cheap)
    session-whitening subspace is fit here, per fold."""
    S = np.asarray(S, dtype=np.float64)
    m_s = S.mean(axis=0)
    Us, es = csa._shrunk_cov(S - m_s, shrinkage)
    inv_sqrt_s = 1.0 / np.sqrt(np.clip(es, eps, None))
    mu_p = np.asarray(mu_p, dtype=np.float64)

    def apply(X):
        Xc = np.asarray(X, dtype=np.float64)
        if Xc.ndim == 1:
            Xc = Xc[None, :]
        Xc = Xc - m_s
        coeff_s = Xc @ Us
        recon_s = (coeff_s * inv_sqrt_s) @ Us.T
        z = recon_s + (Xc - coeff_s @ Us.T)
        coeff_p = z @ Up
        out = (coeff_p * sqrt_ep) @ Up.T + (z - coeff_p @ Up.T)
        return out + mu_p

    return csa.AlignmentTransform("M3_coral", apply,
                                  {"shrinkage": shrinkage, "rank_session": int(Us.shape[1]),
                                   "rank_perception": int(Up.shape[1])})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def loto_preds_ref(X, targets, decoder, method, mu_p, sig_p, P, coral, rand_seed=None):
    """LOTO held-out predictions for M0/M3/M4 and their matched-random controls.
    P is the target-blind perception reference (subsampled); `coral` holds the
    precomputed perception recolor factors (mu_P, Up, sqrt_ep)."""
    uniq = list(dict.fromkeys(targets.tolist()))
    preds = np.empty((X.shape[0], decoder.weights.shape[1]), dtype=np.float64)
    Up_p, sqrt_ep = coral
    for t in uniq:
        te = targets == t
        S = X[~te]
        if method == "M0_identity":
            T = csa.fit_identity()
        elif method == "M3_coral":
            T = build_coral_transform(S, mu_p, Up_p, sqrt_ep, CORAL_SHRINKAGE)
        elif method == "M4_lowrank_moment":
            T = csa.fit_lowrank_moment(S, P, mu_p, rank=M4_RANK)
        elif method == "Mrand_vs_M3":
            # capacity match WITHOUT refitting CORAL's perception SVD: use the
            # session subspace rank as the reference capacity (fold-independent).
            r = int(min(S.shape[0] - 1, mu_p.shape[0]))
            stub = csa.AlignmentTransform("M3_coral", lambda x: x, {"rank_session": r})
            T = csa.fit_matched_random(stub, S, mu_p, seed=rand_seed, rank=r)
        elif method == "Mrand_vs_M4":
            stub = csa.AlignmentTransform("M4_lowrank_moment", lambda x: x, {"rank": M4_RANK})
            T = csa.fit_matched_random(stub, S, mu_p, seed=rand_seed, rank=M4_RANK)
        else:
            raise ValueError(method)
        preds[te] = decoder.predict(T(X[te]))
    return preds


def run_set(name, X, targets, set_cols, pool, decoder, mu_p, sig_p, P, coral):
    out = {"set": name, "n_trials": int(X.shape[0]),
           "n_targets": int(len(set(targets.tolist()))), "set_cols": set_cols}
    per = {}
    for m in ["M0_identity", "M3_coral", "M4_lowrank_moment"]:
        preds = loto_preds_ref(X, targets, decoder, m, mu_p, sig_p, P, coral)
        per[m] = {
            "metrics": within_set_metrics(preds, pool, set_cols, targets),
            "collapse": _collapse_from_predictions(preds, pool, set_cols),
            "heldout_permutation_null": exact_permutation_null_mrr(preds, pool, set_cols, targets),
        }
    base = per["M0_identity"]["metrics"]["mrr"]
    rng = np.random.default_rng(SEED)
    for ref_m, rand_m in (("M3_coral", "Mrand_vs_M3"), ("M4_lowrank_moment", "Mrand_vs_M4")):
        impr = []
        for _ in range(N_MATCHED_RANDOM):
            s = int(rng.integers(0, 2**31 - 1))
            preds = loto_preds_ref(X, targets, decoder, rand_m, mu_p, sig_p, P, coral, rand_seed=s)
            impr.append(within_set_metrics(preds, pool, set_cols, targets)["mrr"] - base)
        impr = np.asarray(impr)
        true_impr = per[ref_m]["metrics"]["mrr"] - base
        per[ref_m]["matched_random"] = {
            "n": N_MATCHED_RANDOM, "true_improvement_over_M0": float(true_impr),
            "random_improvement_95pct": float(np.percentile(impr, 95)),
            "true_exceeds_random_95pct": bool(true_impr > np.percentile(impr, 95)),
        }
    out["methods"] = per
    return out


def main():
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    decoder_path = Path(os.environ["C3M_DECODER"])
    pool_path = Path(os.environ["C3M_POOL"])
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])
    xp_dir = Path(os.environ["XP_DIR"])

    frozen = pickle.load(open(decoder_path, "rb"))
    decoder = frozen["decoder"]
    beta_coords = np.asarray(frozen["beta_coords"])
    mu_p = np.asarray(decoder.voxel_mean, dtype=np.float64)
    sig_p = np.asarray(decoder.voxel_std, dtype=np.float64)
    pool = np.load(pool_path).astype(np.float64)
    manifest = json.load(open(manifest_path))
    rows = manifest["rows"]

    # perception reference X_p: concat rolling-extracted sessions, deterministic subsample
    sess_files = sorted(xp_dir.glob("xp_*_session*.npy"))
    sess_files = [f for f in sess_files if "nsdid" not in f.name]
    P_all = np.concatenate([np.load(f).astype(np.float64) for f in sess_files], axis=0)
    rng = np.random.default_rng(SEED)
    idx = rng.choice(P_all.shape[0], size=min(XP_SUBSAMPLE, P_all.shape[0]), replace=False)
    P = P_all[np.sort(idx)]
    # precompute the perception CORAL recolor subspace ONCE (fold-independent)
    _, Up_p, sqrt_ep = precompute_perception_coral(P, CORAL_SHRINKAGE, CORAL_PERCEPTION_RANK)
    coral = (Up_p, sqrt_ep)

    vis = [r for r in rows if r["event_type"] == "vision" and r["stimulus_set"] in ("A", "B")]
    setA = [r for r in vis if r["stimulus_set"] == "A"]
    setB = [r for r in vis if r["stimulus_set"] == "B"]

    def extract(block):
        idxr = [r["beta_row_index"] for r in block]
        X = extract_imagery_rows(imagery_betas, beta_coords, idxr).astype(np.float64)
        tgt = np.array([r["candidate_pool_index"] for r in block])
        return X, tgt

    XA, tA = extract(setA)
    XB, tB = extract(setB)
    colsA = sorted(set(int(x) for x in tA))
    colsB = sorted(set(int(x) for x in tB))

    result = {
        "artifact": "C3M_VISION_GATE_FAMILY_A_M3M4",
        "gate": "C3M", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal": "VISION_ROWS_ONLY_NO_IMAGERY_LOADED",
        "methods_run": ["M0_identity", "M3_coral", "M4_lowrank_moment"],
        "seed": SEED, "n_matched_random": N_MATCHED_RANDOM,
        "xp_reference": {
            "n_perception_trials_available": int(P_all.shape[0]),
            "n_perception_subsampled": int(P.shape[0]),
            "sessions": [f.name for f in sess_files],
            "beta_version": "betas_fithrf",
        },
        "hyperparams": {"coral_shrinkage": CORAL_SHRINKAGE, "m4_rank": M4_RANK,
                        "coral_perception_rank": CORAL_PERCEPTION_RANK,
                        "xp_subsample": XP_SUBSAMPLE},
        "provenance": {
            "frozen_decoder_weights_hash": frozen["weights_hash"],
            "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
            "imagery_betas_sha256": _sha256_file(imagery_betas),
            "candidate_pool_sha256": _sha256_file(pool_path),
            "event_manifest_hash": manifest.get("manifest_hash"),
            "code_sha": _code_sha(),
        },
        "chance": {"mrr_6cand": 0.408, "two_afc": 0.5},
        "set_B_complex_PRIMARY": run_set("B", XB, tB, colsB, pool, decoder, mu_p, sig_p, P, coral),
        "set_A_simple_OOD": run_set("A", XA, tA, colsA, pool, decoder, mu_p, sig_p, P, coral),
    }
    result["self_hash"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(result, open(results_dir / "c3m_vision_gate_m3m4.json", "w"), indent=2)
    print(f"Wrote {results_dir}/c3m_vision_gate_m3m4.json")
    for sk, sv in (("PRIMARY Set B", result["set_B_complex_PRIMARY"]),
                   ("OOD Set A", result["set_A_simple_OOD"])):
        print(f"\n=== {sk} ===")
        for m, md in sv["methods"].items():
            mm = md["metrics"]; mr = md.get("matched_random")
            line = (f"  {m:20s} MRR={mm['mrr']:.4f} 2AFC={mm['two_afc']:.3f} "
                    f"domfrac={md['collapse']['dominant_fraction']:.3f} "
                    f"effrank={mm['pred_cov_effective_rank']:.2f} "
                    f"p={md['heldout_permutation_null']['p_value']:.4f}")
            if mr:
                line += f" | trueImpr={mr['true_improvement_over_M0']:+.4f} beats95={mr['true_exceeds_random_95pct']}"
            print(line)


if __name__ == "__main__":
    main()

"""C3M primary VISION gate (H2/H3): does a low-capacity, imagery-label-free
session-alignment transform restore stimulus-specific decoding of the
actually-SEEN NSD-Imagery vision trials, on HELD-OUT target identities?

This runner is SEALED against imagery: it reads ONLY the NSD-Imagery *vision*
rows (visA 0:48, visB 192:240). No imagery row is ever loaded, and no imagery
metric is computed. Method/hyperparameter selection uses held-out VISION
performance only (C3M anti-leakage rule).

Family A (target-blind) methods evaluated here:
  M0 identity (== strict C3), M1 mean correction, M2 affine.
Methods that additionally require a core-NSD perception reference X_p
(M3 CORAL, M4 low-rank moment, and Family B M5-M7) are added by
run_c3m_vision_gate_full.py once X_p is certified; this runner deliberately
uses only the frozen decoder's own perception statistics (mu_p, sigma_p).

Evaluation: nested leave-one-target-out (LOTO). For each held-out target the
transform's target-blind statistics are fit on the POOLED, UNLABELED vision
betas of the OTHER targets only (no held-out-target beta enters fitting), the
transform is applied to the held-out target's trials, and those predictions are
decoded with the frozen decoder. Held-out predictions are aggregated across the
6 folds before scoring. Controls: >=200 matched-random transforms (capacity
control) and the exact 6! = 720 held-out target-identity permutation null.

Outputs results/c3m_vision_gate.json with full provenance + self-hash.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from app.research.fmri import cross_session_alignment as csa
from app.research.fmri.decoder import TrainedDecoder  # noqa: F401 (unpickle)
from app.research.fmri.nsdimagery_transfer import extract_imagery_rows

SEED = 20260822
N_MATCHED_RANDOM = 200


# --------------------------------------------------------------------------- #
# provenance helpers
# --------------------------------------------------------------------------- #
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


def _self_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# --------------------------------------------------------------------------- #
# within-set retrieval metrics (restricted to the 6 candidates of the set)
# --------------------------------------------------------------------------- #
def _normrows(A: NDArray) -> NDArray:
    return A / np.clip(np.linalg.norm(A, axis=1, keepdims=True), 1e-8, None)


def within_set_metrics(
    predictions: NDArray, pool: NDArray, set_cols: list[int], true_pool_idx: NDArray
) -> dict:
    """Rank each trial's true target among the `set_cols` candidates only."""
    pred = _normrows(predictions)
    pooln = _normrows(pool)
    sims = pred @ pooln[set_cols].T                    # [n, k]
    set_cols_arr = np.asarray(set_cols)
    # local index of the true target within set_cols
    local_true = np.array([int(np.where(set_cols_arr == t)[0][0]) for t in true_pool_idx])
    n = predictions.shape[0]
    ranks = np.empty(n, dtype=np.int64)
    for i in range(n):
        order = np.argsort(-sims[i])
        ranks[i] = int(np.where(order == local_true[i])[0][0]) + 1
    rr = 1.0 / ranks.astype(np.float64)
    # within-set 2AFC: true candidate more similar than each foil
    n_correct = 0
    n_pairs = 0
    for i in range(n):
        true_sim = sims[i, local_true[i]]
        foils = np.delete(sims[i], local_true[i])
        n_correct += int(np.sum(true_sim > foils))
        n_pairs += foils.shape[0]
    k = len(set_cols)
    return {
        "mrr": float(np.mean(rr)),
        "top1": float(np.mean(ranks == 1)),
        "top3": float(np.mean(ranks <= 3)),
        "median_rank": float(np.median(ranks)),
        "two_afc": float(n_correct / n_pairs) if n_pairs else float("nan"),
        "candidate_entropy": csa.candidate_score_entropy(predictions, pool, set_cols),
        "pred_cov_effective_rank": csa.prediction_covariance_effective_rank(predictions),
        "n_trials": n,
        "mrr_chance_within_set": float(sum(1.0 / r for r in range(1, k + 1)) / k),
        "ranks": ranks.tolist(),
    }


def loto_predictions(
    X: NDArray, targets: NDArray, decoder, method: str, mu_p: NDArray, sig_p: NDArray,
    matched_random_seed: int | None = None,
) -> NDArray:
    """Leave-one-target-out held-out predictions for a Family-A target-blind
    method. Transform stats are fit on the pooled UNLABELED betas of the
    training targets only; the held-out target's trials are transformed and
    decoded. Returns predictions row-aligned to X.
    """
    uniq = list(dict.fromkeys(targets.tolist()))
    preds = np.empty((X.shape[0], decoder.weights.shape[1]), dtype=np.float64)
    for t in uniq:
        te = targets == t
        tr = ~te
        S = X[tr]  # pooled, unlabeled training-target vision betas
        if method == "M0_identity":
            T = csa.fit_identity()
        elif method == "M1_mean_correction":
            T = csa.fit_mean_correction(S, mu_p, per_voxel=True)
        elif method == "M2_affine":
            T = csa.fit_affine(S, mu_p, sig_p)
        elif method == "Mrand_offset_vs_M1":
            ref = csa.fit_mean_correction(S, mu_p, per_voxel=True)
            T = csa.fit_matched_random(ref, S, mu_p, seed=matched_random_seed)
        elif method == "Mrand_vs_M2":
            ref = csa.fit_affine(S, mu_p, sig_p)
            T = csa.fit_matched_random(ref, S, mu_p, seed=matched_random_seed, rank=10)
        else:
            raise ValueError(method)
        preds[te] = decoder.predict(T(X[te]))
    return preds


def exact_permutation_null_mrr(
    predictions: NDArray, pool: NDArray, set_cols: list[int], targets: NDArray,
) -> dict:
    """Exact 6! target-identity permutation null on the held-out predictions.
    Repeat-preserving: permute which physical target each identity group maps to.
    """
    uniq = list(dict.fromkeys(targets.tolist()))
    observed = within_set_metrics(predictions, pool, set_cols, targets)["mrr"]
    null = []
    for perm in itertools.permutations(uniq):
        mapping = {orig: perm[i] for i, orig in enumerate(uniq)}
        permuted = np.array([mapping[t] for t in targets])
        null.append(within_set_metrics(predictions, pool, set_cols, permuted)["mrr"])
    null = np.asarray(null)
    p = float(np.mean(null >= observed - 1e-12))
    return {
        "observed_mrr": observed,
        "null_mean": float(null.mean()),
        "null_95pct": float(np.percentile(null, 95)),
        "null_max": float(null.max()),
        "n_permutations": int(null.size),
        "p_value": p,
    }


def run_set(
    set_name: str, X: NDArray, targets: NDArray, set_cols: list[int], pool: NDArray,
    decoder, mu_p: NDArray, sig_p: NDArray,
) -> dict:
    out: dict = {"set": set_name, "n_trials": int(X.shape[0]),
                 "n_targets": int(len(set(targets.tolist()))), "set_cols": set_cols}
    methods = ["M0_identity", "M1_mean_correction", "M2_affine"]
    per_method = {}
    for m in methods:
        preds = loto_predictions(X, targets, decoder, m, mu_p, sig_p)
        met = within_set_metrics(preds, pool, set_cols, targets)
        # collapse measured on the transformed/decoded predictions
        col = _collapse_from_predictions(preds, pool, set_cols)
        perm = exact_permutation_null_mrr(preds, pool, set_cols, targets)
        per_method[m] = {"metrics": met, "collapse": col, "heldout_permutation_null": perm}

    # matched-random capacity controls (>=200) vs M1 and M2
    rng = np.random.default_rng(SEED)
    for ref_m, rand_m in (("M1_mean_correction", "Mrand_offset_vs_M1"),
                          ("M2_affine", "Mrand_vs_M2")):
        improvements = []
        base_mrr = per_method["M0_identity"]["metrics"]["mrr"]
        for _ in range(N_MATCHED_RANDOM):
            s = int(rng.integers(0, 2**31 - 1))
            preds = loto_predictions(X, targets, decoder, rand_m, mu_p, sig_p,
                                     matched_random_seed=s)
            improvements.append(within_set_metrics(preds, pool, set_cols, targets)["mrr"] - base_mrr)
        improvements = np.asarray(improvements)
        true_impr = per_method[ref_m]["metrics"]["mrr"] - base_mrr
        per_method[ref_m]["matched_random"] = {
            "n": N_MATCHED_RANDOM,
            "true_improvement_over_M0": float(true_impr),
            "random_improvement_mean": float(improvements.mean()),
            "random_improvement_95pct": float(np.percentile(improvements, 95)),
            "true_exceeds_random_95pct": bool(true_impr > np.percentile(improvements, 95)),
        }
    out["methods"] = per_method
    return out


def _collapse_from_predictions(preds: NDArray, pool: NDArray, set_cols: list[int]) -> dict:
    pred = _normrows(preds)
    pooln = _normrows(pool)
    sims = pred @ pooln[set_cols].T
    argmax = np.asarray(set_cols)[sims.argmax(axis=1)]
    counts = {int(c): int((argmax == c).sum()) for c in set_cols}
    n = preds.shape[0]
    top = max(counts, key=counts.get)
    frac = counts[top] / n
    return {"within_set_argmax_counts": counts, "dominant_candidate": top,
            "dominant_fraction": float(frac), "degenerate": bool(frac > 0.5)}


def main() -> None:
    repo = Path(os.environ.get("C3M_REPO", "."))
    results_dir = Path(os.environ.get("RESULTS_DIR", repo / "results"))
    results_dir.mkdir(parents=True, exist_ok=True)

    decoder_path = Path(os.environ["C3M_DECODER"])
    pool_path = Path(os.environ["C3M_POOL"])
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])

    frozen = pickle.load(open(decoder_path, "rb"))
    decoder = frozen["decoder"]
    beta_coords = np.asarray(frozen["beta_coords"])
    mu_p = np.asarray(decoder.voxel_mean, dtype=np.float64)
    sig_p = np.asarray(decoder.voxel_std, dtype=np.float64)

    pool = np.load(pool_path).astype(np.float64)
    manifest = json.load(open(manifest_path))
    rows = manifest["rows"]

    # SEAL: vision rows only
    vis_rows = [r for r in rows if r["event_type"] == "vision"
                and r["stimulus_set"] in ("A", "B")]
    setA = [r for r in vis_rows if r["stimulus_set"] == "A"]
    setB = [r for r in vis_rows if r["stimulus_set"] == "B"]
    assert {r["beta_row_index"] for r in setA} == set(range(0, 48)), "visA rows"
    assert {r["beta_row_index"] for r in setB} == set(range(192, 240)), "visB rows"

    def extract(block):
        idx = [r["beta_row_index"] for r in block]
        X = extract_imagery_rows(imagery_betas, beta_coords, idx).astype(np.float64)
        tgt = np.array([r["candidate_pool_index"] for r in block])
        return X, tgt

    XA, tA = extract(setA)
    XB, tB = extract(setB)
    colsA = sorted(set(int(x) for x in tA))
    colsB = sorted(set(int(x) for x in tB))

    result = {
        "artifact": "C3M_VISION_GATE_FAMILY_A_PARTIAL",
        "gate": "C3M",
        "hypotheses": ["C3M_H1(collapse baseline)", "C3M_H2(vision restore)", "C3M_H3(held-out/random)"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal": "VISION_ROWS_ONLY_NO_IMAGERY_LOADED",
        "methods_run": ["M0_identity", "M1_mean_correction", "M2_affine"],
        "methods_deferred_pending_Xp": ["M3_coral", "M4_lowrank_moment", "M5_ridge", "M6_reduced_rank", "M7_procrustes"],
        "seed": SEED,
        "n_matched_random": N_MATCHED_RANDOM,
        "provenance": {
            "frozen_decoder_weights_hash": frozen["weights_hash"],
            "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
            "imagery_betas_sha256": _sha256_file(imagery_betas),
            "candidate_pool_sha256": _sha256_file(pool_path),
            "event_manifest_hash": manifest.get("manifest_hash"),
            "n_selected_voxels": int(beta_coords.shape[0]),
            "code_sha": _code_sha(),
        },
        "chance": {"mrr_6cand": 0.408, "two_afc": 0.5},
        "set_B_complex_PRIMARY": run_set("B", XB, tB, colsB, pool, decoder, mu_p, sig_p),
        "set_A_simple_OOD": run_set("A", XA, tA, colsA, pool, decoder, mu_p, sig_p),
    }
    result["self_hash"] = _self_hash(result)
    out = results_dir / "c3m_vision_gate.json"
    json.dump(result, open(out, "w"), indent=2)
    print(f"Wrote {out}")

    # concise console summary
    for sk, sv in (("PRIMARY Set B", result["set_B_complex_PRIMARY"]),
                   ("OOD Set A", result["set_A_simple_OOD"])):
        print(f"\n=== {sk} ===")
        for m, md in sv["methods"].items():
            mm = md["metrics"]
            print(f"  {m:22s} MRR={mm['mrr']:.4f} top1={mm['top1']:.3f} "
                  f"2AFC={mm['two_afc']:.3f} domfrac={md['collapse']['dominant_fraction']:.3f} "
                  f"effrank={mm['pred_cov_effective_rank']:.2f} "
                  f"p={md['heldout_permutation_null']['p_value']:.4f}")


if __name__ == "__main__":
    main()

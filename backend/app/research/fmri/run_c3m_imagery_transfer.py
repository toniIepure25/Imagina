"""C3M imagery unblinding (H4): apply the FROZEN, vision-calibrated M3 CORAL
alignment to NSD-Imagery Set-B IMAGERY betas and test for stimulus-specific
perception->imagery transfer. CONDITIONAL on the vision-gate PASS.

Fail-closed: requires results/c3m_alignment_seal.json in state
SEALED_BEFORE_IMAGERY_UNBLINDING with matching frozen input hashes. This is the
FIRST and ONLY place an imagery metric is computed in C3M.

Primary: Set B (imgB rows 336:384 + 624:672, 96 trials). Frozen alignment =
M3 CORAL, session-whitening stats from Set-B VISION betas (target-blind),
perception recolor from X_p, shrinkage 0.1, rank 400. Baselines: M0 identity
(strict C3), M1 imagery mean-shift, capacity-matched random (>=200). Also a
labelled secondary: M3 with session stats from the imagery betas themselves
(target-blind), to separate 'vision correction does not transfer' from 'imagery
carries no decodable content even after its own session correction'.

Exact 6! = 720 target-identity permutation null (repeat-preserving).
Writes results/c3m_imagery_transfer.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
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
from app.research.fmri.run_c3m_vision_robustness import build_coral_random_rotation

SEED_RANDOM = 20260822
N_MATCHED_RANDOM = 200


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def evaluate(preds, pool, cols, targets):
    m = within_set_metrics(preds, pool, cols, targets)
    c = _collapse_from_predictions(preds, pool, cols)
    p = exact_permutation_null_mrr(preds, pool, cols, targets)
    return {"mrr": m["mrr"], "top1": m["top1"], "two_afc": m["two_afc"],
            "dominant_fraction": c["dominant_fraction"], "degenerate": c["degenerate"],
            "candidate_entropy": m["candidate_entropy"],
            "pred_cov_effective_rank": m["pred_cov_effective_rank"],
            "perm_observed_mrr": p["observed_mrr"], "perm_null_mean": p["null_mean"],
            "perm_p_value": p["p_value"], "perm_n": p["n_permutations"]}


def main() -> None:
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    decoder_path = Path(os.environ["C3M_DECODER"])
    pool_path = Path(os.environ["C3M_POOL"])
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])
    xp_dir = Path(os.environ["XP_DIR"])
    seal_path = results_dir / "c3m_alignment_seal.json"

    # ---- fail closed on the seal ----
    if not seal_path.exists():
        sys.exit("FAIL-CLOSED: c3m_alignment_seal.json absent; cannot unblind imagery.")
    seal = json.load(open(seal_path))
    if seal.get("status") != "SEALED_BEFORE_IMAGERY_UNBLINDING":
        sys.exit(f"FAIL-CLOSED: seal status {seal.get('status')!r} != SEALED_BEFORE_IMAGERY_UNBLINDING")
    frozen = pickle.load(open(decoder_path, "rb"))
    checks = {
        "frozen_decoder_weights_hash": frozen["weights_hash"],
        "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
        "imagery_betas_sha256": _sha256_file(imagery_betas),
        "candidate_pool_sha256": _sha256_file(pool_path),
        "event_manifest_hash": json.load(open(manifest_path)).get("manifest_hash"),
    }
    for k, v in checks.items():
        if seal["frozen_input_hashes"].get(k) != v:
            sys.exit(f"FAIL-CLOSED: input hash mismatch for {k}: seal={seal['frozen_input_hashes'].get(k)} now={v}")
    shrink = float(seal["frozen_alignment"]["shrinkage"])
    rank = int(seal["frozen_alignment"]["perception_rank"])

    decoder = frozen["decoder"]
    beta_coords = np.asarray(frozen["beta_coords"])
    mu_p = np.asarray(decoder.voxel_mean, dtype=np.float64)
    pool = np.load(pool_path).astype(np.float64)
    rows = json.load(open(manifest_path))["rows"]

    # ---- perception recolor (frozen X_p) ----
    sess_files = sorted(f for f in xp_dir.glob("xp_*_session*.npy") if "nsdid" not in f.name)
    P_all = np.concatenate([np.load(f).astype(np.float64) for f in sess_files], axis=0)
    rng = np.random.default_rng(SEED_RANDOM)
    P = P_all[np.sort(rng.choice(P_all.shape[0], size=min(2500, P_all.shape[0]), replace=False))]
    _, Up, sqrt_ep = precompute_perception_coral(P, shrink, rank)

    # ---- betas: Set-B VISION (session-stats source) and Set-B IMAGERY (test) ----
    visB = [r for r in rows if r["event_type"] == "vision" and r["stimulus_set"] == "B"]
    imgB = [r for r in rows if r["event_type"] == "imagery" and r["stimulus_set"] == "B"]
    Xv = extract_imagery_rows(imagery_betas, beta_coords, [r["beta_row_index"] for r in visB]).astype(np.float64)
    Xi = extract_imagery_rows(imagery_betas, beta_coords, [r["beta_row_index"] for r in imgB]).astype(np.float64)
    ti = np.array([r["candidate_pool_index"] for r in imgB])
    cols = sorted(set(int(x) for x in ti))
    assert Xi.shape[0] == 96 and len(cols) == 6, (Xi.shape, cols)

    D = decoder
    # ---- FROZEN M3 (primary): session stats from VISION, apply to IMAGERY ----
    T_frozen = build_coral_transform(Xv, mu_p, Up, sqrt_ep, shrink)
    preds_m3_vis = D.predict(T_frozen(Xi))

    # ---- M3 secondary (exploratory): session stats from IMAGERY betas ----
    T_img = build_coral_transform(Xi, mu_p, Up, sqrt_ep, shrink)
    preds_m3_img = D.predict(T_img(Xi))

    # ---- baselines on imagery ----
    preds_m0 = D.predict(Xi)  # strict C3 identity
    m1 = csa.fit_mean_correction(Xi, mu_p, per_voxel=True)  # imagery mean-shift, target-blind
    preds_m1 = D.predict(m1(Xi))

    # ---- capacity-matched random (rank-400 rotation within perception subspace,
    #      vision session whitening), >=200 ----
    rng2 = np.random.default_rng(SEED_RANDOM)
    rand_mrr = []
    for _ in range(N_MATCHED_RANDOM):
        s = int(rng2.integers(0, 2**31 - 1))
        ap = build_coral_random_rotation(Xv, mu_p, Up, sqrt_ep, shrink, s)
        rand_mrr.append(within_set_metrics(D.predict(ap(Xi)), pool, cols, ti)["mrr"])
    rand_mrr = np.asarray(rand_mrr)

    res = {
        "M0_identity_strictC3": evaluate(preds_m0, pool, cols, ti),
        "M1_imagery_mean_shift": evaluate(preds_m1, pool, cols, ti),
        "M3_frozen_from_vision_PRIMARY": evaluate(preds_m3_vis, pool, cols, ti),
        "M3_imagery_session_stats_SECONDARY": evaluate(preds_m3_img, pool, cols, ti),
    }
    m3_mrr = res["M3_frozen_from_vision_PRIMARY"]["mrr"]
    m3 = res["M3_frozen_from_vision_PRIMARY"]
    matched_random = {
        "n": N_MATCHED_RANDOM, "control_mrr_mean": float(rand_mrr.mean()),
        "control_mrr_95pct": float(np.percentile(rand_mrr, 95)),
        "control_mrr_max": float(rand_mrr.max()),
        "m3_exceeds_95pct": bool(m3_mrr > np.percentile(rand_mrr, 95)),
        "m3_exceeds_max": bool(m3_mrr > rand_mrr.max()),
    }

    # ---- decision (frozen guard conditions) ----
    passes = (m3["mrr"] > res["M0_identity_strictC3"]["mrr"]
              and not m3["degenerate"]
              and m3["two_afc"] > 0.5
              and m3["perm_p_value"] < 0.05
              and matched_random["m3_exceeds_95pct"]
              and m3["mrr"] > res["M1_imagery_mean_shift"]["mrr"])
    decision = ("C3M_ALIGNED_IMAGERY_TRANSFER=PASS -> C3M=COMPLETE_WITH_ALIGNED_IMAGERY_TRANSFER"
                if passes else
                "C3M_ALIGNED_IMAGERY_TRANSFER=NULL -> C3M=COMPLETE_WITH_STATE_SPECIFIC_IMAGERY_NULL")

    out = {
        "artifact": "C3M_IMAGERY_TRANSFER",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "seal_status_verified": True,
        "primary_subset": "Set B imagery (96 trials, 6 targets x 16 reps)",
        "chance": {"mrr_6cand": 0.408, "two_afc": 0.5},
        "results": res,
        "matched_random_capacity_control": matched_random,
        "scope": "SINGLE_SUBJECT_subj01_ONLY_NOT_POPULATION_EVIDENCE",
        "aligned_imagery_gate_pass": bool(passes),
        "decision": decision,
        "provenance": {**checks, "code_sha": seal.get("code_sha")},
    }
    out["self_hash"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(out, open(results_dir / "c3m_imagery_transfer.json", "w"), indent=2)
    print(f"Wrote {results_dir}/c3m_imagery_transfer.json\n")
    print(f"chance MRR(6)=0.408  2AFC chance=0.5\n")
    for k, v in res.items():
        print(f"  {k:38s} MRR={v['mrr']:.4f} 2AFC={v['two_afc']:.3f} "
              f"domfrac={v['dominant_fraction']:.3f} effrank={v['pred_cov_effective_rank']:.2f} "
              f"perm_p={v['perm_p_value']:.4f}")
    print(f"\n  matched-random: mean={matched_random['control_mrr_mean']:.3f} "
          f"95pct={matched_random['control_mrr_95pct']:.3f} max={matched_random['control_mrr_max']:.3f} "
          f"| M3 exceeds 95pct={matched_random['m3_exceeds_95pct']}")
    print(f"\nDECISION: {decision}")


if __name__ == "__main__":
    main()

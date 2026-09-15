"""C3XRP precision/power simulation — STUDY DESIGN ONLY (no real neural outcomes).

Synthetic, model-based evaluation of the C3XAT subject-level qualification conjunction (R_I PASS AND
R_P PASS AND cue/video Delta PASS) as a function of the number of independent imagery/perception units
and the true imagery-specific reliability above contamination (Delta truth). Uses the FROZEN estimator
(c3xb_reliability.reliability_with_inference_pairs) and the FROZEN paired-Delta sensitivity + subject
gate from c3xat_pipeline. Reduced inference resamples are used FOR SIMULATION SPEED ONLY (design
planning), not for any confirmatory outcome.

Generative model (shared-latent):
  L_cont[id], L_img[id] : unit-invariant latent patterns (reliable across units).
  pred[u,id]  = sqrt(r_cont)*L_cont[id] + sqrt(1-r_cont)*noise         (contamination-predicted betas)
  obs[u,id]   = sqrt(r_cont)*L_cont[id] + sqrt(r_img)*L_img[id] + sqrt(max(0,1-r_cont-r_img))*noise'
So R_I(pred) ~ r_cont, R_I(obs) ~ r_cont + r_img, and Delta = R_I(obs) - R_I(pred) ~ r_img = delta_truth.
delta_truth=0 (r_img=0) is the strict null (obs and pred share only contamination) -> Type-I check.
"""
from __future__ import annotations

import math

import numpy as np

from app.research.fmri import c3xat_pipeline as P


def simulate_subject(n_units, n_id, vox, delta_truth, r_cont, r_perc, rng):
    """Return (obs, pred, content, unit) for imagery and (pobs, pcontent, punit) for perception."""
    r_img = float(delta_truth)
    L_cont = rng.standard_normal((n_id, vox))
    L_img = rng.standard_normal((n_id, vox))
    L_perc = rng.standard_normal((n_id, vox))
    a_cont = np.sqrt(r_cont)
    a_img = np.sqrt(max(r_img, 0.0))
    a_noise = np.sqrt(max(1.0 - r_cont - max(r_img, 0.0), 1e-6))
    obs, pred, content, unit = [], [], [], []
    for u in range(n_units):
        for i in range(n_id):
            e1 = rng.standard_normal(vox)
            e2 = rng.standard_normal(vox)
            pred.append(a_cont * L_cont[i] + np.sqrt(1 - r_cont) * e2)
            obs.append(a_cont * L_cont[i] + a_img * L_img[i] + a_noise * e1)
            content.append(i)
            unit.append(u)
    # matched perception: reliable content latent, complete identity set per unit
    a_p = np.sqrt(r_perc)
    a_pn = np.sqrt(max(1 - r_perc, 1e-6))
    pobs, pcontent, punit = [], [], []
    for u in range(n_units):
        for i in range(n_id):
            pobs.append(a_p * L_perc[i] + a_pn * rng.standard_normal(vox))
            pcontent.append(i)
            punit.append(u)
    return (np.array(obs), np.array(pred), np.array(content), np.array(unit),
            np.array(pobs), np.array(pcontent), np.array(punit))


def eval_design(n_units, delta_truth, n_id=24, vox=60, r_cont=0.10, r_perc=0.20,
                n_rep=40, seed0=20260909, n_perm=150, n_boot=150):
    """One replicate: simulate a subject and evaluate the frozen conjunction gate.
    Returns dict of booleans + Delta CI width. Uses reduced resamples (design planning only)."""
    rng = np.random.default_rng(seed0)
    obs, pred, content, unit, pobs, pcontent, punit = simulate_subject(
        n_units, n_id, vox, delta_truth, r_cont, r_perc, rng)
    ri = P.reliability_with_inference_pairs(obs, content, unit, P.SEED_BASE, n_perm=n_perm, n_boot=n_boot)
    rp = P.reliability_with_inference_pairs(pobs, pcontent, punit, P.SEED_BASE, n_perm=n_perm, n_boot=n_boot)
    sens = P.paired_delta_sensitivity(obs, pred, content, unit, n_boot=n_boot)
    imagery_pass = P.subject_imagery_pass(ri)
    perception_pass = P.subject_imagery_pass(rp)
    delta_pass = bool(sens["criterion_pass"])
    return {"imagery_pass": imagery_pass, "perception_pass": perception_pass, "delta_pass": delta_pass,
            "joint_pass": bool(imagery_pass and perception_pass and delta_pass),
            "delta_ci_width": float(sens["delta_ci95"][1] - sens["delta_ci95"][0])}


def sweep(units_grid=(5, 7, 9, 12), delta_grid=(0.0, 0.05, 0.08, 0.10, 0.15),
          n_replicates=40, **kw):
    """Estimate pass probabilities (Type-I at delta=0; power otherwise) per (n_units, delta)."""
    out = []
    for n_units in units_grid:
        for delta in delta_grid:
            rec = {"n_units": n_units, "delta_truth": delta}
            agg = {"imagery_pass": 0, "perception_pass": 0, "delta_pass": 0, "joint_pass": 0}
            widths = []
            for r in range(n_replicates):
                res = eval_design(n_units, delta, seed0=20260909 + 1000 * r, **kw)
                for k in agg:
                    agg[k] += int(res[k])
                widths.append(res["delta_ci_width"])
            rec["p_imagery_pass"] = agg["imagery_pass"] / n_replicates
            rec["p_perception_pass"] = agg["perception_pass"] / n_replicates
            rec["p_delta_pass"] = agg["delta_pass"] / n_replicates
            rec["p_joint_pass"] = agg["joint_pass"] / n_replicates
            rec["delta_ci_width_median"] = float(np.median(widths))
            rec["is_type_I"] = (delta == 0.0)
            rec["n_replicates"] = n_replicates
            out.append(rec)
    return out


def required_passes(n_eligible: int) -> int:
    """Generalized cohort qualification threshold, inheriting the C3XAT 2/6 = one-third rule:
    required_passes = max(2, ceil(N/3)). Denominator = all prospectively eligible subjects."""
    return max(2, math.ceil(n_eligible / 3))


def cohort_gate(n_pass: int, n_valid: int, n_eligible: int) -> str:
    """Frozen C3XRP cohort decision. Denominator is fixed from eligible subjects (no shrinkage)."""
    if n_valid < n_eligible:
        return "C3XRP_BLOCKED_INCOMPLETE_MEASUREMENT"
    req = required_passes(n_eligible)
    if n_pass >= req:
        return "C3XRP_REPLICATION_QUALIFIED"
    if n_pass > 0:
        return "C3XRP_REPLICATION_LIMITED"
    return "C3XRP_REPLICATION_FAIL"

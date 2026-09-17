"""C3XRA synthetic analysis driver + scenario generator (design-only; NO human/neural data).

Wraps the FROZEN C3XRP/C3XAT primitives (reliability estimator, paired-Delta sensitivity, subject PASS,
cohort gate) into a single driver, and generates synthetic scenarios — including adversarial leakage /
fingerprint / shuffle cases — so the end-to-end pipeline can be replayed and its guarantees checked WITHOUT
any real data. The contamination-predicted betas (`pred`) are built to contain EXACTLY zero true-imagery
contribution, so a valid primary Delta PASS can only arise from genuine imagery-specific reliability.
"""
from __future__ import annotations

import numpy as np

from app.research.fmri import c3xat_pipeline as P
from app.research.fmri import c3xrp_precision as PR

# Sealed confirmatory inference (the numbers a real run would use).
SEALED_INFERENCE = {"n_perm": 1000, "n_boot": 1000, "n_rep_point": 200,
                    "seed": P.SEED_BASE, "seed_offsets": [0, 100, 200]}


def build_pred_contamination(L_cont, content, unit, r_cont, rng, vox):
    """Contamination-predicted betas from cue+post-video ONLY: a_cont*L_cont[id] + noise. Contains NO
    L_img term by construction -> the paired Delta subtracts exactly the contamination channel."""
    a = np.sqrt(r_cont)
    pred = []
    for u in range(int(max(unit)) + 1):
        for i in sorted(set(int(c) for c in content)):
            pred.append(a * L_cont[i] + np.sqrt(max(1 - r_cont, 1e-6)) * rng.standard_normal(vox))
    return np.asarray(pred)


def simulate_scenario(name, n_units=7, n_id=24, vox=60, seed=20260909):
    """Return (obs, pred, content, unit, pobs, pcontent, punit, meta). `pred` is always the contamination
    channel with zero imagery. Scenarios cover null/signal/leakage/fingerprint/shuffle cases."""
    rng = np.random.default_rng(seed)
    L_cont = rng.standard_normal((n_id, vox))
    L_img = rng.standard_normal((n_id, vox))
    L_perc = rng.standard_normal((n_id, vox))

    cfg = {
        "strict_null":              dict(r_cont=0.25, r_img=0.00, r_perc=0.35),
        "imagery_only":             dict(r_cont=0.00, r_img=0.15, r_perc=0.35),
        "imagery_plus_contam":      dict(r_cont=0.25, r_img=0.15, r_perc=0.35),
        "perception_stable_img_null": dict(r_cont=0.10, r_img=0.00, r_perc=0.45),
        "cue_only":                 dict(r_cont=0.30, r_img=0.00, r_perc=0.35),
        "postvideo_only":           dict(r_cont=0.30, r_img=0.00, r_perc=0.35),
        "delta_zero":               dict(r_cont=0.20, r_img=0.00, r_perc=0.35),
        "delta_positive":           dict(r_cont=0.15, r_img=0.15, r_perc=0.35),
        "motion":                   dict(r_cont=0.10, r_img=0.13, r_perc=0.35, motion=True),
        "session_effects":          dict(r_cont=0.10, r_img=0.13, r_perc=0.35, session=True),
        # adversarial: must NOT yield a valid primary joint PASS
        "adv_perfect_cue_leakage":  dict(r_cont=0.30, r_img=0.00, r_perc=0.35, obs_equals_pred=True),
        "adv_perfect_postvideo_leakage": dict(r_cont=0.30, r_img=0.00, r_perc=0.35, obs_equals_pred=True),
        "adv_session_fingerprint_no_identity": dict(r_cont=0.00, r_img=0.00, r_perc=0.35, fingerprint=True),
        "adv_identity_shuffled_within": dict(r_cont=0.10, r_img=0.20, r_perc=0.35, shuffle_within=True),
        "adv_identity_shuffled_across": dict(r_cont=0.10, r_img=0.20, r_perc=0.35, shuffle_across=True),
    }[name]

    r_cont, r_img, r_perc = cfg["r_cont"], cfg["r_img"], cfg["r_perc"]
    a_cont, a_img = np.sqrt(r_cont), np.sqrt(max(r_img, 0.0))
    a_noise = np.sqrt(max(1 - r_cont - max(r_img, 0.0), 1e-6))

    obs, content, unit = [], [], []
    session_shift = [rng.standard_normal(vox) for _ in range(n_units)]
    for u in range(n_units):
        # per-unit identity relabeling for shuffle-adversarial cases
        if cfg.get("shuffle_within"):
            perm = rng.permutation(n_id)           # obs uses shuffled identity, labels stay canonical
        elif cfg.get("shuffle_across"):
            perm = rng.permutation(n_id)
        else:
            perm = np.arange(n_id)
        for i in range(n_id):
            src = perm[i]
            if cfg.get("fingerprint"):
                v = session_shift[u] + a_noise * rng.standard_normal(vox)   # no identity term at all
            else:
                v = a_cont * L_cont[i] + a_img * L_img[src] + a_noise * rng.standard_normal(vox)
            if cfg.get("motion"):
                v = v + 0.5 * session_shift[u]      # per-run motion-like nuisance (content-independent)
            if cfg.get("session"):
                v = v + 0.8 * session_shift[u]
            obs.append(v)
            content.append(i)
            unit.append(u)
    obs = np.asarray(obs)
    content = np.asarray(content)
    unit = np.asarray(unit)

    pred = build_pred_contamination(L_cont, content, unit, r_cont, rng, vox)
    if cfg.get("obs_equals_pred"):
        obs = pred.copy()                           # perfect leakage: observed == contamination prediction

    # perception (matched complete-content units)
    a_p, a_pn = np.sqrt(r_perc), np.sqrt(max(1 - r_perc, 1e-6))
    pobs, pcontent, punit = [], [], []
    for u in range(n_units):
        for i in range(n_id):
            pobs.append(a_p * L_perc[i] + a_pn * rng.standard_normal(vox))
            pcontent.append(i)
            punit.append(u)
    meta = {"scenario": name, **cfg,
            "pred_has_zero_imagery": float(np.abs(_pattern_corr(pred, L_img, content)) )}
    return (obs, pred, content, unit, np.asarray(pobs), np.asarray(pcontent), np.asarray(punit), meta)


def _pattern_corr(betas, latent, content):
    """Mean |corr| between each identity's mean beta pattern and its L_img latent — verifies pred carries
    no imagery. Near 0 = contamination channel is imagery-free."""
    betas = np.asarray(betas)
    content = np.asarray(content)
    cs = sorted(set(int(c) for c in content))
    vals = []
    for i in cs:
        m = betas[content == i].mean(0)
        a = m - m.mean()
        b = latent[i] - latent[i].mean()
        d = np.linalg.norm(a) * np.linalg.norm(b)
        if d > 1e-9:
            vals.append(abs(float(a @ b / d)))
    return float(np.mean(vals)) if vals else 0.0


def analyze_subject(obs, pred, content, unit, pobs, pcontent, punit,
                    n_perm=200, n_boot=200):
    """Run the frozen primary conjunction on one synthetic subject. (Replay uses reduced resamples for
    speed; SEALED_INFERENCE holds the confirmatory numbers.)"""
    ri = P.reliability_with_inference_pairs(obs, content, unit, P.SEED_BASE, n_perm=n_perm, n_boot=n_boot)
    rp = P.reliability_with_inference_pairs(pobs, pcontent, punit, P.SEED_BASE, n_perm=n_perm, n_boot=n_boot)
    sens = P.paired_delta_sensitivity(obs, pred, content, unit, n_boot=n_boot)
    imagery_pass = P.subject_imagery_pass(ri)
    perception_pass = P.subject_imagery_pass(rp)
    delta_pass = bool(sens["criterion_pass"])
    return {"imagery_pass": imagery_pass, "perception_pass": perception_pass, "delta_pass": delta_pass,
            "joint_pass": bool(imagery_pass and perception_pass and delta_pass),
            "R_I": ri["reliability"], "R_I_perm_p": ri["perm_p_one_sided"],
            "R_P": rp["reliability"], "delta_point": sens["delta_point"],
            "delta_ci_lo": sens["delta_ci95"][0]}


def cohort_decision(n_pass, n_valid, n_eligible):
    return PR.cohort_gate(n_pass, n_valid, n_eligible)

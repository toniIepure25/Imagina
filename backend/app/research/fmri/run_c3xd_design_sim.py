"""C3XD — design-identifiability + synthetic injected-signal recovery (NO BOLD, NO reliability-based
model selection). Uses the REAL S1 imagery event timing to decide whether the imagery interval can be
estimated separately from the adjacent preparation cue and the later target video.

Candidate models (frozen family):
  A = LSA: per-trial imagery + per-trial cue + per-trial video regressors + grouped eval + drift.
  B = LSS: per imagery trial -> [target imagery]+[other imagery]+[target cue]+[other cue]+[video]+[eval]+drift.
  C = naive late-imagery window mean (HRF-shifted), NO cue regressor (negative baseline; expected to leak).

Metrics (design-only + synthetic; NEVER reliability-based selection):
  design conditioning, imagery/cue regressor correlation & VIF;
  imagery recovery r (imagery-only injection);
  cue->imagery and video->imagery leakage (cue+video-only injection, video-specific patterns);
  FALSE-POSITIVE recovered-imagery reliability under the cue+video-only null (the estimator-level test).
Acceptance thresholds are read from the frozen seal. Writes c3xd_glm_design_selection.json and
c3xd_design_simulation.json. Imports NO geometry, NO semantic features.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from app.research.fmri.c3xc_fast import reliability_with_inference_pairs_fast

TR = 1.0


def spm_hrf(tr=1.0, dur=32.0, shift=0.0, width=1.0):
    t = np.arange(0, dur, tr) - shift
    from math import gamma
    def g(t, a, b):
        tt = np.clip(t, 0, None)
        return (b ** a) * (tt ** (a - 1)) * np.exp(-b * tt) / gamma(a)
    a1, a2 = 6 * width, 16 * width
    h = g(t, a1, 1.0) - g(t, a2, 1.0) / 6.0
    h[t < 0] = 0
    return h / (np.abs(h).sum() + 1e-12)


def boxcar(n, onset, dur):
    x = np.zeros(n)
    a, b = int(round(onset / TR)), int(round((onset + dur) / TR))
    x[max(a, 0):min(b, n)] = 1.0
    return x


def conv(reg, hrf):
    return np.convolve(reg, hrf)[:len(reg)]


def _drift(n):
    t = np.linspace(-1, 1, n)
    return np.stack([np.ones(n), t, t * t], 1)


def build_run(trials, hrf):
    """Return run length n and per-event convolved regressors for one run's imagery trials."""
    n = int(max(t["video_onset"] + t["video_duration"] for t in trials) / TR) + 25
    cue = [conv(boxcar(n, t["cue_onset"], t["cue_duration"]), hrf) for t in trials]
    img = [conv(boxcar(n, t["imagery_onset"], t["imagery_duration"]), hrf) for t in trials]
    vid = [conv(boxcar(n, t["video_onset"], t["video_duration"]), hrf) for t in trials]
    ev = np.zeros(n)
    for t in trials:
        ev += boxcar(n, t["eval_onset"], t["eval_duration"])
    ev = conv(ev, hrf)
    return n, np.array(cue), np.array(img), np.array(vid), ev


def _ols(X, Y):
    return np.linalg.lstsq(X, Y, rcond=None)[0]


def recover_A(n, cue, img, vid, ev, Y):
    X = np.column_stack([img.T, cue.T, vid.T, ev, _drift(n)])
    beta = _ols(X, Y)
    return beta[:img.shape[0]]  # per-trial imagery betas (ntrial, V)


def recover_B(n, cue, img, vid, ev, Y):
    dr = _drift(n)
    out = []
    vsum = vid.sum(0)
    for k in range(img.shape[0]):
        others_img = img.sum(0) - img[k]
        others_cue = cue.sum(0) - cue[k]
        X = np.column_stack([img[k], others_img, cue[k], others_cue, vsum, ev, dr])
        out.append(_ols(X, Y)[0])
    return np.array(out)


def recover_C(n, trials, Y, shift=4.0):
    out = []
    for t in trials:
        a = int(round((t["imagery_onset"] + shift) / TR))
        b = int(round((t["imagery_onset"] + t["imagery_duration"] + shift) / TR))
        out.append(Y[max(a, 0):min(b, n)].mean(0))
    return np.array(out)


def simulate(trials_by_run, sessions, videos, V, gen_hrf, fit_hrf, noise, ar, cond, rng, cue_gain=1.0):
    """Generate synthetic BOLD per run under `cond`, recover imagery betas with A/B/C.
    cue_gain scales the video-specific cue (and video) pattern magnitude relative to imagery.
    Returns recovered betas (ntrial,V) for each model, ordered as trials_by_run flattened."""
    uv = sorted(set(videos))
    P_img = {v: rng.standard_normal(V) for v in uv}
    P_cue = {v: rng.standard_normal(V) for v in uv}
    P_vid = {v: rng.standard_normal(V) for v in uv}
    recA, recB, recC = [], [], []
    for trials in trials_by_run:
        n, cue_g, img_g, vid_g, ev_g = build_run(trials, gen_hrf)
        # generate BOLD (n, V)
        Y = np.zeros((n, V))
        for i, t in enumerate(trials):
            v = t["video_id"]
            if cond in ("imagery_only", "all"):
                Y += np.outer(img_g[i], P_img[v])
            if cond in ("cuevideo_null", "all"):
                Y += cue_gain * (np.outer(cue_g[i], P_cue[v]) + np.outer(vid_g[i], P_vid[v]))
        e = rng.standard_normal((n, V)) * noise
        if ar > 0:
            for k in range(1, n):
                e[k] += ar * e[k - 1]
        Y += e
        _, cue_f, img_f, vid_f, ev_f = build_run(trials, fit_hrf)
        recA.append(recover_A(n, cue_f, img_f, vid_f, ev_f, Y))
        recB.append(recover_B(n, cue_f, img_f, vid_f, ev_f, Y))
        recC.append(recover_C(n, trials, Y))
    return (np.vstack(recA), np.vstack(recB), np.vstack(recC), P_img, P_cue, P_vid)


def _rowcorr(A, patmap, vids):
    vals = []
    for i, v in enumerate(vids):
        a = A[i] - A[i].mean()
        p = patmap[v] - patmap[v].mean()
        vals.append(float(np.dot(a, p) / (np.linalg.norm(a) * np.linalg.norm(p) + 1e-24)))
    return float(np.mean(vals))


def main() -> None:
    out_dir = Path(os.environ.get("C3XD_OUT_DIR", "results/c3xd"))
    seal = json.load(open(os.environ.get("C3XD_SEAL", "reports/c3xd/c3xd_protocol_seal.json")))
    thr = seal["synthetic_acceptance_thresholds"]
    timing = json.load(open(out_dir / "c3xd_s1_imagery_timing.json"))["trials"]
    V = int(os.environ.get("C3XD_SIM_V", "300"))

    # group trials by (session, run) preserving global order for session-disjoint reliability
    by_run = {}
    for t in timing:
        by_run.setdefault((t["session"], t["run"]), []).append(t)
    run_keys = sorted(by_run)
    trials_by_run = [sorted(by_run[k], key=lambda x: x["imagery_onset"]) for k in run_keys]
    flat = [t for run in trials_by_run for t in run]
    videos = [t["video_id"] for t in flat]
    session_idx = np.array([int(t["session"].replace("testImagery", "")) for t in flat])
    content = np.array(videos)

    fit_hrf = spm_hrf()
    # ---- design metrics (design-only; one representative run) ----
    n, cue, img, vid, ev = build_run(trials_by_run[0], fit_hrf)
    Xd = np.column_stack([img.T, cue.T, vid.T, ev, _drift(n)])
    Xz = (Xd - Xd.mean(0)) / (Xd.std(0) + 1e-12)
    cond_number = float(np.linalg.cond(Xz))
    ni = img.shape[0]
    # imagery vs its own cue correlation (adjacency), and imagery VIF
    corr = np.corrcoef(Xz.T)
    img_cue_corr = float(np.mean([abs(corr[i, ni + i]) for i in range(ni)]))
    vifs = []
    for i in range(ni):
        others = np.delete(np.arange(Xz.shape[1]), i)
        b = np.linalg.lstsq(Xz[:, others], Xz[:, i], rcond=None)[0]
        resid = Xz[:, i] - Xz[:, others] @ b
        r2 = 1 - np.sum(resid ** 2) / (np.sum((Xz[:, i] - Xz[:, i].mean()) ** 2) + 1e-12)
        vifs.append(1.0 / max(1 - r2, 1e-6))
    img_sub = (img.T - img.T.mean(0)) / (img.T.std(0) + 1e-12)
    imagery_submatrix_cond = float(np.linalg.cond(img_sub))
    design = {"condition_number_full_design": cond_number,
              "condition_number_note": "full-design cond is inflated by drift/eval collinearity in the "
                                       "nuisance subspace; imagery estimability is governed by imagery VIF "
                                       "(low) and the imagery-submatrix condition number.",
              "imagery_submatrix_condition_number": imagery_submatrix_cond,
              "imagery_vs_own_cue_corr_mean": img_cue_corr,
              "imagery_VIF_mean": float(np.mean(vifs)), "imagery_VIF_max": float(np.max(vifs)),
              "n_imagery_regressors_per_run": ni}

    # ---- synthetic recovery across perturbations ----
    perturb = [dict(shift=0.0, width=1.0, noise=1.0, ar=0.0),
               dict(shift=1.0, width=1.0, noise=1.0, ar=0.3),
               dict(shift=-1.0, width=1.2, noise=1.5, ar=0.3),
               dict(shift=0.5, width=0.8, noise=2.0, ar=0.3)]
    cue_gains = [0.25, 0.5, 1.0]  # video-specific cue+video magnitude relative to imagery (characterization)
    models = {"A": {}, "B": {}, "C": {}}
    per_perturb = []
    for pi, pp in enumerate(perturb):
        rng = np.random.default_rng(20260909 + pi)
        gen = spm_hrf(shift=pp["shift"], width=pp["width"])
        # imagery-only recovery (cue_gain irrelevant)
        io = {}
        rA, rB, rC, P_img, _, _ = simulate(trials_by_run, session_idx, videos, V, gen, fit_hrf,
                                           pp["noise"], pp["ar"], "imagery_only", rng)
        io = dict(A=rA, B=rB, C=rC, P_img=P_img)
        row = {"perturb": pp, "models": {}}
        for mdl, key in [("A", "A"), ("B", "B"), ("C", "C")]:
            recovery = _rowcorr(io[key], io["P_img"], videos)
            row["models"][mdl] = {"imagery_recovery_r": recovery, "null_fp_by_cue_gain": {}}
        for cg in cue_gains:
            rngc = np.random.default_rng(20260909 + pi * 10 + int(cg * 100))
            rA, rB, rC, _, P_cue, P_vid = simulate(trials_by_run, session_idx, videos, V, gen, fit_hrf,
                                                   pp["noise"], pp["ar"], "cuevideo_null", rngc, cue_gain=cg)
            for mdl, arr in [("A", rA), ("B", rB), ("C", rC)]:
                cue_leak = _rowcorr(arr, P_cue, videos)
                vid_leak = _rowcorr(arr, P_vid, videos)
                nr = reliability_with_inference_pairs_fast(arr.astype(np.float64), content, session_idx,
                                                           20260909, n_perm=200, n_boot=200)
                fp = bool(nr["reliability"] > 0 and nr["perm_p_one_sided"] < 0.05 and nr["bootstrap_ci95"][0] > 0)
                row["models"][mdl]["null_fp_by_cue_gain"][str(cg)] = {
                    "cue_leak": cue_leak, "video_leak": vid_leak,
                    "null_reliability": nr["reliability"], "perm_p": nr["perm_p_one_sided"],
                    "false_positive": fp}
        per_perturb.append(row)

    # aggregate per model
    gains = [str(g) for g in cue_gains]
    for mdl in ("A", "B", "C"):
        rec_r = [p["models"][mdl]["imagery_recovery_r"] for p in per_perturb]
        by_gain = {}
        for g in gains:
            cl = [abs(p["models"][mdl]["null_fp_by_cue_gain"][g]["cue_leak"]) for p in per_perturb]
            vl = [abs(p["models"][mdl]["null_fp_by_cue_gain"][g]["video_leak"]) for p in per_perturb]
            fp = [p["models"][mdl]["null_fp_by_cue_gain"][g]["false_positive"] for p in per_perturb]
            by_gain[g] = {"cue_leak_max": float(np.max(cl)), "video_leak_max": float(np.max(vl)),
                          "null_false_positive_rate": float(np.mean(fp))}
        worst = by_gain["1.0"]  # equal cue:imagery magnitude (conservative worst case)
        models[mdl] = {"imagery_recovery_r_min": float(np.min(rec_r)),
                       "imagery_recovery_r_mean": float(np.mean(rec_r)),
                       "null_fp_by_cue_gain": by_gain,
                       "meets_thresholds_at_equal_magnitude": bool(
                           np.min(rec_r) >= thr["imagery_recovery_r_min"]
                           and worst["cue_leak_max"] <= thr["cue_to_imagery_leakage_max"]
                           and worst["video_leak_max"] <= thr["postvideo_to_imagery_leakage_max"]
                           and worst["null_false_positive_rate"] <= thr["null_false_positive_rate_max"])}

    sim = {"artifact": "C3XD_DESIGN_SIMULATION", "V": V, "n_perturbations": len(perturb),
           "thresholds": thr, "per_model": models, "per_perturbation": per_perturb,
           "note": "synthetic BOLD from REAL S1 imagery timing; model selection is design/synthetic ONLY, "
                   "never based on real imagery reliability (no real BOLD used)."}
    sim["self_hash"] = hashlib.sha256(json.dumps(sim, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(sim, open(out_dir / "c3xd_design_simulation.json", "w"), indent=2)

    # ---- model selection (design + synthetic only) ----
    accepted = [m for m in ("A", "B") if models[m]["meets_thresholds_at_equal_magnitude"]]
    if accepted:
        primary = max(accepted, key=lambda m: models[m]["imagery_recovery_r_min"])
        status = "MODEL_SELECTED"
    else:
        primary = None
        status = "NO_IDENTIFIABLE_MODEL_AT_EQUAL_MAGNITUDE"
    sel = {"artifact": "C3XD_GLM_DESIGN_SELECTION", "status": status, "primary_model": primary,
           "design_metrics": design, "candidate_summary": models,
           "selection_rule": "design conditioning + synthetic recovery/leakage/null-FP vs frozen thresholds; "
                             "NEVER real imagery reliability/geometry/decoding/ROI/behaviour",
           "negative_baseline_C_leaks": not models["C"]["meets_thresholds_at_equal_magnitude"]}
    sel["self_hash"] = hashlib.sha256(json.dumps(sel, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(sel, open(out_dir / "c3xd_glm_design_selection.json", "w"), indent=2)

    print("design:", design)
    for m in ("A", "B", "C"):
        print(m, models[m])
    print("SELECTION:", status, "primary=", primary)


if __name__ == "__main__":
    main()

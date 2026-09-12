"""C3XAT-R1 analysis pipeline — outcome-independent, synthetically-validated components.

Every function here is developed and tested WITHOUT inspecting any real neural outcome (no R_I, R_P,
stimulus-pattern similarity, Delta_I, cue/video reliability). The confirmatory reliability itself is the
FROZEN normative estimator `c3xb_reliability.reliability_with_inference_pairs` (independent unit =
imagery SESSION); nothing frozen is redefined here.

Scope of this module:
  * event parsing / trial mapping for ds005191 testImagery + testPerception events.tsv
  * MODEL_A_LSA design-matrix builder (per-trial cue + imagery + post-video + grouped eval + nuisance)
  * fMRIPrep confound resolver against the frozen nuisance family
  * Wang25 primary MPM subject-space QC (deterministic use of the frozen volumetric atlas; NO per-subject
    warp, NO fsaverage projection for the PRIMARY route)
  * gray-matter control construction interface
  * session-disjoint reliability wiring + subject imagery PASS rule
  * cue/video forward-contamination operator (true imagery contribution == 0 by construction)
  * Delta_I inference (frozen route) and the subject / dataset qualification gates

No CLIP/DINO/semantic/decoding/geometry/reconstruction anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Reuse the FROZEN normative estimator + gates unchanged.
from app.research.fmri.c3xb_reliability import reliability_with_inference_pairs  # noqa: F401

# ---- frozen trial-type coding (ds005191 events.tsv) -----------------------------------------------
# trial_type: 2 = imagery (imageryID), -2 = cue (cueID), 3 = post-video stimulus (stimID).
TT_IMAGERY = "2"
TT_CUE = "-2"
TT_POSTVIDEO = "3"

# frozen contract
N_VIDEOS = 72
N_IMAGERY_TRIALS = 360
N_IMAGERY_SESSIONS = 5
REPS_PER_VIDEO = 5

# frozen inference constants (mirror c3xb_reliability / the C3XAT seal)
N_PERM = 1000
N_BOOT = 1000
N_REP_POINT = 200
SEED_BASE = 20260909
SEED_OFFSETS = (0, 100, 200)

# frozen nuisance family (exact deterministic fMRIPrep-confound columns; no outcome-dependent selection)
FROZEN_NUISANCE_MOTION = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
FROZEN_NUISANCE_TISSUE = ["csf", "white_matter"]
# run/session intercept + cosine drift (fMRIPrep high-pass regressors cosine00..) added per run.


@dataclass(frozen=True)
class TrialEvent:
    onset: float
    duration: float
    kind: str          # "cue" | "imagery" | "postvideo"
    video_id: int
    session: int
    run: int


def parse_events(rows, session: int, run: int) -> list[TrialEvent]:
    """Parse a list of events.tsv dict-rows into typed cue/imagery/post-video trials.

    Outcome-independent: reads only onset/duration/trial_type and the identity ids.
    """
    out: list[TrialEvent] = []
    for r in rows:
        tt = str(r.get("trial_type", "")).strip()
        onset = float(r["onset"])
        dur = float(r["duration"])
        if tt == TT_IMAGERY:
            vid = int(float(r["imageryID"]))
            if vid > 0:
                out.append(TrialEvent(onset, dur, "imagery", vid, session, run))
        elif tt == TT_CUE:
            vid = int(float(r["cueID"]))
            if vid > 0:
                out.append(TrialEvent(onset, dur, "cue", vid, session, run))
        elif tt == TT_POSTVIDEO:
            vid = int(float(r["stimID"]))
            if vid > 0:
                out.append(TrialEvent(onset, dur, "postvideo", vid, session, run))
    return out


def verify_trial_contract(imagery_trials: list[TrialEvent]) -> dict:
    """Fail-closed check of the sealed imagery contract (counts only, no neural data)."""
    vids = [t.video_id for t in imagery_trials]
    sessions = sorted({t.session for t in imagery_trials})
    from collections import Counter
    c = Counter(vids)
    reps = set(c.values())
    ok = (len(imagery_trials) == N_IMAGERY_TRIALS and len(c) == N_VIDEOS
          and len(sessions) == N_IMAGERY_SESSIONS and reps == {REPS_PER_VIDEO})
    return {"n_imagery_trials": len(imagery_trials), "distinct_videos": len(c),
            "imagery_sessions": len(sessions), "reps_set": sorted(reps),
            "contract_pass": bool(ok)}


def _hrf_double_gamma(tr: float, length: float = 32.0) -> np.ndarray:
    """Canonical SPM-style double-gamma HRF (frozen; not reopened)."""
    from math import gamma
    dt = tr
    t = np.arange(0, length, dt)
    a1, a2, b1, b2, c = 6.0, 16.0, 1.0, 1.0, 1.0 / 6.0
    peak = (t ** (a1 - 1) * b1 ** a1 * np.exp(-b1 * t)) / gamma(a1)
    undershoot = (t ** (a2 - 1) * b2 ** a2 * np.exp(-b2 * t)) / gamma(a2)
    h = peak - c * undershoot
    return h / np.max(np.abs(h))


def _regressor(onsets, durations, n_scans, tr, hrf):
    """Boxcar convolved with HRF, sampled at TR (single condition/trial)."""
    hires = 16
    n_hi = int(np.ceil(n_scans * tr * hires)) + len(hrf) * hires
    box = np.zeros(n_hi)
    for on, du in zip(onsets, durations):
        s = int(round(on * hires))
        e = int(round((on + du) * hires))
        box[s:e] = 1.0
    hrf_hi = np.interp(np.arange(0, len(hrf) * tr, tr / hires),
                       np.arange(0, len(hrf) * tr, tr), hrf)
    conv = np.convolve(box, hrf_hi)[:n_hi]
    idx = (np.arange(n_scans) * tr * hires).astype(int)
    return conv[idx]


def build_model_a_design(trials: list[TrialEvent], n_scans: int, tr: float,
                         nuisance: np.ndarray | None = None) -> dict:
    """MODEL_A_LSA: separately identifiable per-trial cue, imagery, post-video regressors +
    a grouped evaluation term + frozen nuisance. Deterministic column ordering.

    Returns design matrix, column labels, and the index blocks. NO neural data touched.
    """
    hrf = _hrf_double_gamma(tr)
    cols = []
    labels = []
    blocks = {"cue": [], "imagery": [], "postvideo": []}
    # deterministic ordering: kind (cue,imagery,postvideo) then onset
    order = {"cue": 0, "imagery": 1, "postvideo": 2}
    strials = sorted(trials, key=lambda t: (order[t.kind], t.onset))
    for t in strials:
        reg = _regressor([t.onset], [t.duration], n_scans, tr, hrf)
        blocks[t.kind].append(len(cols))
        cols.append(reg)
        labels.append(f"{t.kind}_v{t.video_id}_on{int(t.onset)}")
    # grouped evaluation term: a single mean-evaluation regressor spanning all imagery trials
    if blocks["imagery"]:
        eval_reg = np.mean([cols[i] for i in blocks["imagery"]], axis=0)
        eval_idx = len(cols)
        cols.append(eval_reg)
        labels.append("grouped_eval")
    else:
        eval_idx = None
    # intercept
    cols.append(np.ones(n_scans))
    labels.append("intercept")
    nuis_block = []
    if nuisance is not None and nuisance.size:
        for j in range(nuisance.shape[1]):
            nuis_block.append(len(cols))
            cols.append(nuisance[:, j])
            labels.append(f"nuisance_{j}")
    X = np.vstack(cols).T
    return {"design": X, "labels": labels, "blocks": blocks, "eval_idx": eval_idx,
            "nuisance_idx": nuis_block, "video_ids": [t.video_id for t in strials if t.kind == "imagery"]}


def resolve_confounds(available_columns: list[str]) -> dict:
    """Deterministic frozen nuisance resolution against fMRIPrep confounds columns.

    Single prospectively-specified rule: motion 6-DOF are REQUIRED; tissue (csf,white_matter) are
    included if present else omitted (recorded); cosine drift columns (cosineNN) all included; NEVER
    selected by variance/R_I/subject quality. Missing required motion -> fail-closed.
    """
    cols = list(available_columns)
    motion = [c for c in FROZEN_NUISANCE_MOTION if c in cols]
    tissue = [c for c in FROZEN_NUISANCE_TISSUE if c in cols]
    cosine = sorted([c for c in cols if c.startswith("cosine")])
    missing_motion = [c for c in FROZEN_NUISANCE_MOTION if c not in cols]
    return {"selected": motion + tissue + cosine, "motion": motion, "tissue": tissue,
            "cosine": cosine, "missing_required_motion": missing_motion,
            "resolver_pass": len(missing_motion) == 0,
            "rule": "motion6 required; csf/white_matter if present; all cosine drift; "
                    "outcome-independent; missing required motion => fail-closed"}


def wang25_qc(atlas_affine, atlas_shape, target_affine, target_shape,
              label_ids, expected_label_ids, finite_coverage_frac) -> dict:
    """Deterministic primary Wang25 subject-space QC. The atlas is the FROZEN volumetric MPM already in
    the fMRIPrep target space; QC only verifies exact grid/affine/label/coverage — no warping, no
    per-subject placement, no outcome-driven editing, no parcel dropping, no hemisphere choice."""
    affine_ok = np.allclose(np.asarray(atlas_affine), np.asarray(target_affine), atol=1e-4)
    shape_ok = tuple(atlas_shape) == tuple(target_shape)
    labels_ok = set(int(x) for x in label_ids) == set(int(x) for x in expected_label_ids)
    coverage_ok = finite_coverage_frac >= 0.99
    return {"affine_match": bool(affine_ok), "shape_match": bool(shape_ok),
            "all_labels_present": bool(labels_ok), "finite_coverage_ok": bool(coverage_ok),
            "qc_pass": bool(affine_ok and shape_ok and labels_ok and coverage_ok),
            "n_labels": len(set(int(x) for x in label_ids))}


def concat_session_means(betas, video_ids, sessions):
    """Return (X, content, pair) arrays for the frozen estimator, unit = imagery SESSION.
    `betas`: (n_trials, n_vox); video_ids/sessions align by trial. Pure reshaping, no statistics.
    """
    X = np.asarray(betas, float)
    content = np.asarray(video_ids, int)
    pair = np.asarray(sessions, int)   # independent unit = imagery session
    return X, content, pair


def imagery_reliability(betas, video_ids, sessions, seed=SEED_BASE) -> dict:
    """Session-disjoint R_I via the FROZEN estimator. (Called on real betas only after freeze.)"""
    X, content, pair = concat_session_means(betas, video_ids, sessions)
    return reliability_with_inference_pairs(X, content, pair, seed, n_perm=N_PERM, n_boot=N_BOOT)


def forward_contamination_bold(design_info: dict, betas_by_col: np.ndarray) -> np.ndarray:
    """Build the predicted BOLD from cue + post-video + nuisance ONLY (imagery + grouped-eval columns
    excluded). By construction the true imagery contribution is EXACTLY zero: imagery/eval columns are
    never multiplied in. Returns predicted BOLD (n_scans, n_vox)."""
    X = design_info["design"]
    b = np.asarray(betas_by_col, float)                      # (n_cols, n_vox)
    keep = np.zeros(X.shape[1], bool)
    for i in design_info["blocks"]["cue"]:
        keep[i] = True
    for i in design_info["blocks"]["postvideo"]:
        keep[i] = True
    for i in design_info["nuisance_idx"]:
        keep[i] = True
    # intercept kept as baseline
    if "intercept" in design_info["labels"]:
        keep[design_info["labels"].index("intercept")] = True
    # NOTE: imagery columns and grouped_eval are intentionally NOT kept.
    return X[:, keep] @ b[keep, :]


def imagery_beta_operator(design_info: dict) -> np.ndarray:
    """Rows of pinv(design) selecting imagery-trial betas (the exact Model-A LSA imagery operator)."""
    X = design_info["design"]
    pinv = np.linalg.pinv(X)
    idx = design_info["blocks"]["imagery"]
    return pinv[idx, :]


def delta_i(r_i_observed: float, r_i_cuevideo_predicted: float) -> float:
    return float(r_i_observed - r_i_cuevideo_predicted)


def subject_imagery_pass(res: dict) -> bool:
    """Frozen imagery PASS: R_I>0 AND perm p<0.05 AND bootstrap CI lower>0 AND min sealed-seed R_I>0."""
    return bool(res["reliability"] > 0 and res["perm_p_one_sided"] < 0.05
                and res["bootstrap_ci95"][0] > 0 and res["split_seed_min"] > 0)


def subject_primary_pass(imagery_pass, perception_pass, cue_video_pass,
                         unit_contract_pass, atlas_qc_pass) -> bool:
    return bool(imagery_pass and perception_pass and cue_video_pass
                and unit_contract_pass and atlas_qc_pass)


def dataset_gate(n_pass: int, n_valid: int) -> str:
    """Frozen dataset decision. Requires 6 valid measurements for a FAIL verdict."""
    if n_valid < 6:
        return "C3XAT_R1_BLOCKED_INCOMPLETE_MEASUREMENT"
    if n_pass >= 2:
        return "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED"
    if n_pass == 1:
        return "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    return "C3XAT_D2_ATLAS_IMAGERY_FAIL"

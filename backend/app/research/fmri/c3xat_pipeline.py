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

# Reuse the EXACT historical C3XD Model-A canonical-HRF / boxcar / convolution primitives so the
# scientific cue/imagery/video/eval regressors are, by construction, identical to the original
# C3XD/C3XDR Model A (proven bit-identical in test_c3xat_pipeline against run_c3xd_design_sim.build_run).
from app.research.fmri.run_c3xd_design_sim import conv as c3xd_conv
from app.research.fmri.run_c3xd_design_sim import spm_hrf as c3xd_spm_hrf

# ---- frozen trial-type coding (ds005191 events.tsv) -----------------------------------------------
# trial_type: 2 = imagery (imageryID), -2 = cue (cueID), 3 = post-video stimulus (stimID),
#             -5 = evaluation (grouped, unmodulated; the ORIGINAL C3XD Model-A eval regressor).
TT_IMAGERY = "2"
TT_CUE = "-2"
TT_POSTVIDEO = "3"
TT_EVAL = "-5"

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
        elif tt == TT_EVAL:
            # grouped evaluation event: NO video identity, NO vividness/accuracy modulation.
            out.append(TrialEvent(onset, dur, "eval", 0, session, run))
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


def _boxcar_tr(n_scans: int, onset: float, duration: float, tr: float) -> np.ndarray:
    """TR-parameterised boxcar. At tr==1.0 this is bit-identical to the historical C3XD
    run_c3xd_design_sim.boxcar (same int(round(onset/tr)) edge rounding)."""
    x = np.zeros(n_scans)
    a = int(round(onset / tr))
    b = int(round((onset + duration) / tr))
    x[max(a, 0):min(b, n_scans)] = 1.0
    return x


def canonical_hrf(tr: float) -> np.ndarray:
    """The EXACT frozen C3XD canonical HRF (imported primitive; not a re-implementation)."""
    return c3xd_spm_hrf(tr=tr)


def build_model_a_design(trials: list[TrialEvent], n_scans: int, tr: float,
                         nuisance: np.ndarray | None = None) -> dict:
    """MODEL_A_LSA, exactly as C3XD/C3XDR: per-trial imagery + per-trial cue + per-trial post-video
    regressors + ONE grouped evaluation regressor built from the REAL trial_type=-5 evaluation events
    (unmodulated; no video identity; no vividness/accuracy), + frozen nuisance.

    Scientific regressors use the imported C3XD spm_hrf/conv (+ tr-parameterised boxcar), so at tr=1.0
    they are bit-identical to run_c3xd_design_sim.build_run. Deterministic column ordering:
    imagery block, cue block, post-video block, grouped_eval, intercept, nuisance. NO neural data.
    """
    hrf = canonical_hrf(tr)
    cols: list[np.ndarray] = []
    labels: list[str] = []
    blocks = {"imagery": [], "cue": [], "postvideo": []}
    # deterministic ordering matching C3XD recover_A: imagery, cue, video; each sub-block by onset
    order = {"imagery": 0, "cue": 1, "postvideo": 2}
    trial_kinds = [t for t in trials if t.kind in order]
    strials = sorted(trial_kinds, key=lambda t: (order[t.kind], t.onset))
    for t in strials:
        reg = c3xd_conv(_boxcar_tr(n_scans, t.onset, t.duration, tr), hrf)
        blocks[t.kind].append(len(cols))
        cols.append(reg)
        labels.append(f"{t.kind}_v{t.video_id}_on{int(t.onset)}")
    # grouped evaluation: sum of REAL eval-event boxcars, then convolved (C3XD build_run semantics).
    eval_events = [t for t in trials if t.kind == "eval"]
    eval_idx = None
    if eval_events:
        ev = np.zeros(n_scans)
        for t in eval_events:
            ev = ev + _boxcar_tr(n_scans, t.onset, t.duration, tr)
        eval_idx = len(cols)
        cols.append(c3xd_conv(ev, hrf))
        labels.append("grouped_eval")
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


def design_rank_audit(design_info: dict) -> dict:
    """Metadata-only technical audit of a Model-A design: shape, rank, rank deficiency, imagery
    submatrix condition number, max |cue-imagery| correlation, and max imagery VIF. No neural data."""
    X = design_info["design"]
    blocks = design_info["blocks"]
    rank = int(np.linalg.matrix_rank(X))
    deficiency = int(X.shape[1] - rank)
    imag = X[:, blocks["imagery"]] if blocks["imagery"] else np.zeros((X.shape[0], 0))
    cond = float(np.linalg.cond(imag)) if imag.shape[1] > 1 else 1.0
    # max |correlation| between any cue and any imagery regressor
    max_cue_img = 0.0
    for ci in blocks["cue"]:
        for ii in blocks["imagery"]:
            a = X[:, ci] - X[:, ci].mean()
            b = X[:, ii] - X[:, ii].mean()
            d = (np.linalg.norm(a) * np.linalg.norm(b))
            if d > 0:
                max_cue_img = max(max_cue_img, abs(float(np.dot(a, b) / d)))
    # max imagery VIF: regress each imagery col on all OTHER design cols
    max_vif = 1.0
    others_all = list(range(X.shape[1]))
    for ii in blocks["imagery"]:
        rest = [j for j in others_all if j != ii]
        A = X[:, rest]
        y = X[:, ii]
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2)) + 1e-24
        r2 = 1.0 - ss_res / ss_tot
        r2 = min(max(r2, 0.0), 1.0 - 1e-12)
        max_vif = max(max_vif, 1.0 / (1.0 - r2))
    return {"shape": list(X.shape), "rank": rank, "rank_deficiency": deficiency,
            "imagery_condition_number": cond, "max_abs_cue_imagery_corr": float(max_cue_img),
            "max_imagery_vif": float(max_vif), "n_imagery": len(blocks["imagery"])}


def delta_i(r_i_observed: float, r_i_cuevideo_predicted: float) -> float:
    return float(r_i_observed - r_i_cuevideo_predicted)


# ---- conservative PAIRED Delta sensitivity (sealed fallback; NOT a fixed-R_pred permutation) -------
from app.research.fmri.c3x_reliability import _r_from_halves  # noqa: E402
from app.research.fmri.c3xb_reliability import (  # noqa: E402
    _split_pairs,  # noqa: E402
    run_pair_disjoint_reliability,
)


def _means_over_pairs(X, content, pair, sel_pairs, ids):
    rows = []
    for c in ids:
        vecs = []
        for p in sel_pairs:
            idx = np.where((pair == p) & (content == c))[0]
            if len(idx):
                vecs.append(X[idx].mean(0))
        if vecs:
            rows.append((c, np.mean(vecs, 0)))
    return dict(rows)


def _r_for_split(X, content, pair, pa, pb, ids):
    ma, mb = _means_over_pairs(X, content, pair, pa, ids), _means_over_pairs(X, content, pair, pb, ids)
    common = [c for c in ids if c in ma and c in mb]
    if len(common) < 2:
        return None
    A = np.asarray([ma[c] for c in common])
    B = np.asarray([mb[c] for c in common])
    return _r_from_halves(A, B)


def paired_delta_sensitivity(obs_betas, pred_betas, content, pair,
                             seeds=(SEED_BASE, SEED_BASE + 100, SEED_BASE + 200),
                             n_boot=N_BOOT) -> dict:
    """Sealed conservative PAIRED Delta sensitivity. For every bootstrap realization the SAME imagery-
    session split + resample is applied to BOTH observed and cue/video-predicted betas (never independent
    bootstraps). Criterion: Delta point > 0 AND paired bootstrap 95% CI lower > 0 AND Delta > 0 under
    every sealed split-seed. Primary R_I keeps its own frozen permutation p unchanged."""
    content = np.asarray(content)
    pair = np.asarray(pair)
    ids = sorted(set(int(c) for c in content))
    upairs = sorted(set(int(p) for p in pair.tolist()))
    # point Delta at base seed via the frozen point estimator
    d_point = float(run_pair_disjoint_reliability(obs_betas, content, pair, seeds[0])
                    - run_pair_disjoint_reliability(pred_betas, content, pair, seeds[0]))
    # paired bootstrap (shared split + shared resample indices for obs and pred)
    rng = np.random.default_rng(seeds[0] + 2)
    deltas = []
    for _ in range(n_boot):
        pa, pb = _split_pairs(upairs, rng)
        pa = rng.choice(pa, len(pa), replace=True)
        pb = rng.choice(pb, len(pb), replace=True)
        r_obs = _r_for_split(obs_betas, content, pair, pa, pb, ids)
        r_pred = _r_for_split(pred_betas, content, pair, pa, pb, ids)
        if r_obs is not None and r_pred is not None:
            deltas.append(r_obs - r_pred)
    deltas = np.asarray(deltas)
    ci = [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))]
    per_seed = [float(run_pair_disjoint_reliability(obs_betas, content, pair, s)
                     - run_pair_disjoint_reliability(pred_betas, content, pair, s)) for s in seeds]
    d_min = float(min(per_seed))
    passed = bool(d_point > 0 and ci[0] > 0 and d_min > 0)
    return {"delta_point": d_point, "delta_ci95": ci, "delta_bootstrap_mean": float(deltas.mean()),
            "per_seed_delta": per_seed, "delta_min_seed": d_min, "n_boot": int(n_boot),
            "seeds": list(seeds), "paired": True, "method": "SEALED_CONSERVATIVE_SENSITIVITY",
            "criterion_pass": passed}


def certify_five_session_splits(unit_ids, n_rep=N_REP_POINT,
                                seeds=(SEED_BASE, SEED_BASE + 100, SEED_BASE + 200)) -> dict:
    """Certify (metadata-only) the FROZEN c3xb `_split_pairs` behaviour on 5 imagery sessions: every
    split is 2 vs 2 disjoint with exactly 1 omitted, halves never overlap, and across the frozen
    n_rep-repeat campaign under every sealed seed all five sessions participate. Records omission
    frequencies. Does NOT modify the estimator (uses its own splitter)."""
    from collections import Counter
    units = sorted(int(u) for u in unit_ids)
    omit = Counter()
    participate = set()
    all_ok = True
    n_splits = 0
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for _ in range(n_rep):
            pa, pb = _split_pairs(units, rng)
            pa_s, pb_s = set(int(x) for x in pa), set(int(x) for x in pb)
            n_splits += 1
            if pa_s & pb_s:
                all_ok = False
            used = pa_s | pb_s
            if len(pa_s) != 2 or len(pb_s) != 2 or len(used) != 4:
                all_ok = False
            omitted = set(units) - used
            if len(omitted) != 1:
                all_ok = False
            for o in omitted:
                omit[o] += 1
            participate |= used
    return {"n_sessions": len(units), "each_split_4_distinct_and_1_omitted": bool(all_ok),
            "halves_never_overlap": bool(all_ok), "all_sessions_participate": participate == set(units),
            "omission_counts": {str(k): int(v) for k, v in sorted(omit.items())},
            "n_splits_examined": n_splits, "scientific_estimator_changed": False}


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

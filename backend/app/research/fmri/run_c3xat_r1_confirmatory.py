"""C3XAT-R1 confirmatory campaign driver — runs the SEALED analysis on real fMRIPrep derivatives.

Imports the FROZEN, synthetically-validated pipeline (c3xat_pipeline) and the FROZEN estimator
(c3xb_reliability). Computes, per subject, in the certified WANG25 primary ROI:
  R_I (session-disjoint, frozen estimator), R_P (perception-run-disjoint), the cue/video forward-
  contamination predicted reliability R_I_cuevideo_predicted, Delta_I, and the sealed conservative
  PAIRED Delta sensitivity; then applies the frozen subject PASS rule and dataset gate.

Per-run LSA (MODEL_A_LSA): design built by c3xat_pipeline.build_model_a_design (bit-identical C3XD),
nuisance = the frozen fMRIPrep-confound set (resolve_confounds); betas = pinv(X) @ Y_roi per run;
imagery-trial betas are the sealed content patterns. NO scientific parameter is chosen here; this driver
only executes frozen code. Run ONLY after the implementation-freeze commit. Writes per-subject result
JSON to the workspace; no outcome is inspected before the freeze.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/opt/app")  # cluster: repo mounted/installed; falls back to installed package
from app.research.fmri import c3xat_pipeline as P  # noqa: E402

RAW_BIDS = os.environ.get("C3XAT_RAW_BIDS", "/work/ds005191")


def _raw_events_path(deriv_bold_path: str) -> str:
    """events.tsv live in the RAW BIDS tree (fMRIPrep does not copy them into derivatives)."""
    stem = os.path.basename(deriv_bold_path).split("_space-")[0]  # sub-XX_ses-..._task-..._run-YY
    sub = stem.split("_")[0]
    ses = [t for t in stem.split("_") if t.startswith("ses-")][0]
    return f"{RAW_BIDS}/{sub}/{ses}/func/{stem}_events.tsv"


def _raw_bold_json(deriv_bold_path: str) -> str:
    stem = os.path.basename(deriv_bold_path).split("_space-")[0]
    sub = stem.split("_")[0]
    ses = [t for t in stem.split("_") if t.startswith("ses-")][0]
    return f"{RAW_BIDS}/{sub}/{ses}/func/{stem}_bold.json"


def _tr_of(deriv_bold_path: str) -> float:
    # RepetitionTime from the RAW BIDS bold sidecar (authoritative)
    side = _raw_bold_json(deriv_bold_path)
    if os.path.exists(side):
        return float(json.load(open(side))["RepetitionTime"])
    dside = deriv_bold_path.replace(".nii.gz", ".json")
    if os.path.exists(dside):
        return float(json.load(open(dside))["RepetitionTime"])
    raise FileNotFoundError(f"no bold sidecar for {deriv_bold_path}")


def _load_run(bold_path, events_path, confounds_path, roi_idx, tr):
    import nibabel as nib
    bold = nib.load(bold_path)
    data = np.asanyarray(bold.dataobj)             # X,Y,Z,T
    n_scans = data.shape[3]
    Y = data.reshape(-1, n_scans)[roi_idx, :].T.astype(np.float64)  # (T, n_roivox)
    ev_rows = pd.read_csv(events_path, sep="\t").to_dict("records")
    # confounds -> frozen nuisance columns
    conf = pd.read_csv(confounds_path, sep="\t")
    sel = P.resolve_confounds(list(conf.columns))
    if not sel["resolver_pass"]:
        raise RuntimeError(f"nuisance resolver failed: missing {sel['missing_required_motion']}")
    nuis = conf[sel["selected"]].fillna(0.0).to_numpy(dtype=np.float64)[:n_scans, :]
    return n_scans, Y, ev_rows, nuis


def _session_of(path: str) -> int:
    # ses-testImagery03 -> 3 ; ses-testPerception02 -> 2
    for tok in path.split(os.sep):
        if tok.startswith("ses-testImagery"):
            return int(tok.replace("ses-testImagery", ""))
        if tok.startswith("ses-testPerception"):
            return int(tok.replace("ses-testPerception", ""))
    raise ValueError(path)


def _betas_for_task(deriv, sub, task, roi_idx):
    """Per-run LSA imagery/perception betas + matched cue/video contamination-predicted betas."""
    patt = f"{deriv}/{sub}/ses-{task}*/func/*space-MNI152NLin2009cAsym*desc-preproc_bold.nii.gz"
    runs = sorted(glob.glob(patt))
    obs, pred, content, unit = [], [], [], []
    n_used = 0
    for bp in runs:
        ep = _raw_events_path(bp)  # events.tsv from RAW BIDS
        cp = bp.replace("_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz",
                        "_desc-confounds_timeseries.tsv")
        if not (os.path.exists(ep) and os.path.exists(cp)):
            continue
        n_used += 1
        tr = _tr_of(bp)
        n_scans, Y, ev_rows, nuis = _load_run(bp, ep, cp, roi_idx, tr)
        trials = P.parse_events(ev_rows, session=_session_of(bp), run=1)
        d = P.build_model_a_design(trials, n_scans, tr, nuisance=nuis)
        X = d["design"]
        pinv = np.linalg.pinv(X)
        betas = pinv @ Y                              # (n_cols, n_roivox)
        imag_idx = d["blocks"]["imagery"]
        if not imag_idx:
            continue
        b_img = betas[imag_idx, :]                    # observed imagery-trial betas
        # cue/video forward contamination -> predicted imagery betas (zero true-imagery contribution)
        pred_bold = P.forward_contamination_bold(d, betas)          # (T, n_roivox)
        b_pred = pinv[imag_idx, :] @ pred_bold                      # predicted imagery betas
        vids = [t.video_id for t in sorted([t for t in trials if t.kind == "imagery"],
                                           key=lambda t: t.onset)]
        # imagery block is ordered by onset within the imagery sub-block (see build_model_a_design)
        sess = _session_of(bp)
        run_unit = sess if task == "testImagery" else (100 * sess + int(
            bp.split("_run-")[1].split("_")[0]))     # perception unit = RUN
        for k in range(b_img.shape[0]):
            obs.append(b_img[k])
            pred.append(b_pred[k])
            content.append(vids[k])
            unit.append(run_unit)
    if n_used == 0 or len(obs) == 0:
        raise RuntimeError(f"fail-closed: no usable {task} runs for {sub} "
                           f"(runs found={len(runs)}, used={n_used}); check raw events/confound paths")
    return (np.asarray(obs), np.asarray(pred), np.asarray(content), np.asarray(unit))


def run_subject(deriv, sub, roi_idx) -> dict:
    # imagery: independent unit = SESSION
    obs, pred, content, sess = _betas_for_task(deriv, sub, "testImagery", roi_idx)
    ri = P.reliability_with_inference_pairs(obs, content, sess, P.SEED_BASE, n_perm=P.N_PERM, n_boot=P.N_BOOT)
    ri_pred = P.reliability_with_inference_pairs(pred, content, sess, P.SEED_BASE,
                                                 n_perm=P.N_PERM, n_boot=P.N_BOOT)
    delta = P.delta_i(ri["reliability"], ri_pred["reliability"])
    sens = P.paired_delta_sensitivity(obs, pred, content, sess)
    # perception: independent unit = RUN
    pobs, _pp, pcontent, prun = _betas_for_task(deriv, sub, "testPerception", roi_idx)
    rp = P.reliability_with_inference_pairs(pobs, pcontent, prun, P.SEED_BASE, n_perm=P.N_PERM, n_boot=P.N_BOOT)
    imagery_pass = P.subject_imagery_pass(ri)
    perception_pass = P.subject_imagery_pass(rp)
    cuevideo_pass = bool(sens["criterion_pass"])
    unit_contract_pass = bool(len(set(int(s) for s in sess)) == P.N_IMAGERY_SESSIONS
                              and len(set(int(c) for c in content)) == P.N_VIDEOS)
    primary_pass = P.subject_primary_pass(imagery_pass, perception_pass, cuevideo_pass,
                                          unit_contract_pass, True)
    return {"subject": sub,
            "R_I": ri["reliability"], "perm_p": ri["perm_p_one_sided"], "bootstrap_ci95": ri["bootstrap_ci95"],
            "split_seed_min_R_I": ri["split_seed_min"], "split_seed_values_R_I": ri["split_seed_values"],
            "R_P": rp["reliability"], "R_P_perm_p": rp["perm_p_one_sided"], "R_P_ci95": rp["bootstrap_ci95"],
            "R_P_split_seed_min": rp["split_seed_min"],
            "R_I_cuevideo_predicted": ri_pred["reliability"], "Delta_I": delta,
            "paired_delta": sens,
            "imagery_pass": imagery_pass, "perception_pass": perception_pass,
            "cuevideo_pass": cuevideo_pass, "unit_contract_pass": unit_contract_pass,
            "atlas_qc_pass": True, "primary_pass": primary_pass,
            "n_imagery_trials": int(obs.shape[0]), "n_perception_trials": int(pobs.shape[0]),
            "n_roi_voxels": int(len(roi_idx))}


def main():
    deriv = os.environ.get("C3XAT_DERIV", "/work/run2/deriv")
    mask = os.environ["C3XAT_ROI_MASK"]
    out = os.environ.get("C3XAT_OUT", "/work/wang/results")
    os.makedirs(out, exist_ok=True)
    import nibabel as nib
    roi = np.asanyarray(nib.load(mask).dataobj) > 0
    roi_idx = np.where(roi.reshape(-1))[0]
    subs = os.environ.get("C3XAT_SUBS", "sub-01,sub-02,sub-03,sub-04,sub-05,sub-06").split(",")
    for sub in subs:
        r = run_subject(deriv, sub, roi_idx)
        json.dump(r, open(f"{out}/confirmatory_{sub}.json", "w"), indent=2)
        print(f"DONE {sub} R_I={r['R_I']:.4f} p={r['perm_p']:.4f} R_P={r['R_P']:.4f} "
              f"Delta={r['Delta_I']:.4f} pass={r['primary_pass']}")


if __name__ == "__main__":
    main()

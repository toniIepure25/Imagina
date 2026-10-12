"""Offline fMRI validation on Haxby et al. (2001) via nilearn ``fetch_haxby`` (perception only).

Checks the ``processing.fmri`` path end to end: BIDS discovery (data rewritten into a BIDS-like layout), TR handling,
design matrix and GLM against nilearn ``FirstLevelModel``, and category decoding from ventral temporal (VT) cortex
with leave-one-run-out cross-validation. The dataset has no imagery condition, so fMRI imagery decoding is BLOCKED
here; nothing in this gate speaks to imagery.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.multimodal.processing.fmri import design_matrix, discover_bids, fit_glm, roi_timeseries
from app.multimodal.validation.gates import Criterion, GateResult

TR = 2.5
SUBJECTS = [1, 2, 3, 4, 5, 6]
CATEGORIES = ["bottle", "cat", "chair", "face", "house", "scissors", "scrambledpix", "shoe"]
N_PERM = 200
SEED = 20261013

CRITERIA = [
    Criterion("glm_t_median_corr_vs_nilearn", ">=", 0.95, 0.80,
              "Same events, TR, SPM-style HRF and cosine drift: voxelwise t-maps should agree closely; residual "
              "differences come from HRF shape and oversampling."),
    Criterion("eightway_accuracy_ci_low", ">=", 0.30, 0.20,
              "Chance is 0.125. VT category decoding on this dataset is well above chance in published work; a CI "
              "lower bound of 0.30 shows the pipeline preserves category information."),
    Criterion("face_house_accuracy_ci_low", ">=", 0.80, 0.60, "Faces vs houses is the strongest VT contrast."),
    Criterion("max_subject_perm_p", "<=", 0.01, 0.05,
              "Every subject's 8-way accuracy must beat a within-run label-permutation null."),
    Criterion("rest_control_abs_deviation", "<=", 0.05, 0.10,
              "Rest segments with arbitrary labels must decode at chance (pipeline does not create structure)."),
]


def to_bids(sub: int, func: str, labels_path: str, mask_vt: str, out: Path) -> None:
    import nibabel as nib

    lines = Path(labels_path).read_text().strip().splitlines()[1:]
    labels = np.array([ln.split()[0] for ln in lines])
    chunks = np.array([int(ln.split()[1]) for ln in lines])
    img = nib.load(func)
    data = np.asarray(img.dataobj, dtype=np.float32)
    d = out / f"sub-{sub}" / "func"
    d.mkdir(parents=True, exist_ok=True)
    m = nib.load(mask_vt)
    nib.save(nib.Nifti1Image(np.asarray(m.dataobj).astype(np.uint8), m.affine), d / f"sub-{sub}_roi-vt_mask.nii.gz")
    for run in np.unique(chunks):
        stem = f"sub-{sub}_task-objects_run-{run + 1:02d}"
        if (d / f"{stem}_events.tsv").exists():
            continue
        idx = np.where(chunks == run)[0]
        nib.save(nib.Nifti1Image(data[..., idx], img.affine), d / f"{stem}_bold.nii.gz")
        (d / f"{stem}_bold.json").write_text(json.dumps({"RepetitionTime": TR}))
        lab = labels[idx]
        rows = ["onset\tduration\ttrial_type"]
        start = 0
        for k in range(1, lab.size + 1):
            if k == lab.size or lab[k] != lab[start]:
                kind = lab[start] if lab[start] != "rest" else "rest"
                rows.append(f"{start * TR:.2f}\t{(k - start) * TR:.2f}\t{kind}")
                start = k
        (d / f"{stem}_events.tsv").write_text("\n".join(rows) + "\n")


def _boot_ci(x: np.ndarray, n: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    means = rng.choice(x, size=(n, x.size), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _loro_accuracy(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    correct = 0
    for g in np.unique(groups):
        tr, te = groups != g, groups == g
        assert not set(groups[tr]) & set(groups[te])
        clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
        clf.fit(x[tr], y[tr])
        correct += int((clf.predict(x[te]) == y[te]).sum())
    return correct / y.size


def _perm_within_run(y: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    yp = y.copy()
    for g in np.unique(groups):
        i = np.where(groups == g)[0]
        yp[i] = rng.permutation(y[i])
    return yp


def _nilearn_t(run, conditions: list[str]) -> dict[str, np.ndarray]:
    import pandas as pd
    from nilearn.glm.first_level import FirstLevelModel
    from nilearn.maskers import NiftiMasker

    ev = pd.DataFrame([e for e in run.events if e["trial_type"] in conditions])
    flm = FirstLevelModel(t_r=run.tr, slice_time_ref=0.5, hrf_model="spm", drift_model="cosine", high_pass=1 / 128,
                          noise_model="ols", signal_scaling=False, standardize=False, mask_img=str(run.mask_path),
                          minimize_memory=True)
    flm.fit(str(run.bold_path), events=ev)
    masker = NiftiMasker(mask_img=str(run.mask_path)).fit()
    return {c: masker.transform(flm.compute_contrast(c, stat_type="t", output_type="stat")).ravel() for c in conditions}


def run(root: Path) -> GateResult:
    import nilearn
    from nilearn import datasets

    bids = root / "haxby_bids"
    used = []
    for s in SUBJECTS:
        try:
            h = datasets.fetch_haxby(data_dir=str(root), subjects=[s], fetch_stimuli=False, verbose=0)
        except Exception as e:  # noqa: BLE001
            print(f"subject {s} unavailable: {e!r}"[:200])
            continue
        to_bids(s, h.func[0], h.session_target[0], h.mask_vt[0], bids)
        used.append(s)
    runs = discover_bids(bids)
    rng = np.random.default_rng(SEED)
    per_subject, glm_corr = [], []
    for s in used:
        sub_runs = [r for r in runs if r.subject == f"sub-{s}"]
        betas, labels, groups, rest_b, rest_y, rest_g = [], [], [], [], [], []
        for k, r in enumerate(sub_runs):
            y = roi_timeseries(r)
            conds = [c for c in CATEGORIES if any(e["trial_type"] == c for e in r.events)]
            x, names = design_matrix(r, y.shape[0], conds)
            beta, t = fit_glm(y, x)
            for c in conds:
                betas.append(beta[names.index(c)])
                labels.append(c)
                groups.append(k)
            if k < 2:
                ref = _nilearn_t(r, conds)
                glm_corr.extend(float(np.corrcoef(t[names.index(c)], ref[c])[0, 1]) for c in conds)
            rest = [e for e in r.events if e["trial_type"] == "rest" and e["onset"] > 0][:8]
            pseudo = rng.permutation(len(rest))
            for j, e in enumerate(rest):
                r_ctrl = type(r)(**{**r.__dict__, "events": [{**e, "trial_type": "ctrl"}]})
                xc, nc = design_matrix(r_ctrl, y.shape[0], ["ctrl"])
                rest_b.append(fit_glm(y, xc)[0][nc.index("ctrl")])
                rest_y.append(int(pseudo[j]))
                rest_g.append(k)
        xb, yb, gb = np.array(betas), np.array(labels), np.array(groups)
        acc8 = _loro_accuracy(xb, yb, gb)
        null = np.array([_loro_accuracy(xb, _perm_within_run(yb, gb, rng), gb) for _ in range(N_PERM)])
        fh = np.isin(yb, ["face", "house"])
        acc_fh = _loro_accuracy(xb[fh], yb[fh], gb[fh])
        rest_acc = _loro_accuracy(np.array(rest_b), np.array(rest_y), np.array(rest_g))
        n_rest_classes = len(set(rest_y))
        per_subject.append({"subject": f"sub-{s}", "n_runs": len(sub_runs), "n_voxels_vt": int(xb.shape[1]),
                            "n_samples": int(yb.size), "eightway_accuracy": acc8,
                            "eightway_perm_p": float((1 + (null >= acc8).sum()) / (1 + N_PERM)),
                            "eightway_null_mean": float(null.mean()), "face_house_accuracy": acc_fh,
                            "rest_control_accuracy": rest_acc, "rest_control_chance": 1 / n_rest_classes})
        print(per_subject[-1], flush=True)
    acc8 = np.array([p["eightway_accuracy"] for p in per_subject])
    fh = np.array([p["face_house_accuracy"] for p in per_subject])
    rest_dev = float(np.mean([p["rest_control_accuracy"] - p["rest_control_chance"] for p in per_subject]))
    g = GateResult(
        experiment="FMRI_GLM_DECODING_HAXBY",
        dataset={"name": "Haxby et al. 2001 (nilearn fetch_haxby)", "nilearn_version": nilearn.__version__,
                 "subjects_used": [f"sub-{s}" for s in used], "tr_s": TR},
        participants={"n": len(used), "ids": "dataset subject numbers (public, already pseudonymous)"},
        task_and_labels="Block design, 8 visual object categories per run (perception only; no imagery).",
        design="Per-run GLM (our design_matrix/fit_glm, canonical HRF, cosine drift 128 s) on VT voxels -> one beta "
               "pattern per category per run; leave-one-run-out logistic regression; scaler fit on training runs.",
        metric_definitions={"glm_t_median_corr_vs_nilearn": "median over (subject, first two runs, condition) of the "
                            "voxelwise Pearson r between our t and nilearn FirstLevelModel t in VT",
                            "eightway_accuracy_ci_low": "2.5th percentile of subject-bootstrap mean 8-way accuracy",
                            "max_subject_perm_p": f"max over subjects of the within-run permutation p ({N_PERM} perms)",
                            "rest_control_abs_deviation": "|mean(rest-segment accuracy - chance)| with arbitrary "
                                                          "labels on rest segments"},
        criteria=CRITERIA,
        results={"per_subject": per_subject, "eightway_mean": float(acc8.mean()), "eightway_ci": _boot_ci(acc8),
                 "face_house_mean": float(fh.mean()), "face_house_ci": _boot_ci(fh),
                 "glm_t_corr": {"median": float(np.median(glm_corr)), "min": float(np.min(glm_corr)),
                                "n": len(glm_corr)},
                 "imagery": {"verdict": "BLOCKED", "reason": "dataset has no imagery condition; NOD closed for "
                                                             "development; no other local fMRI imagery data"}},
        baseline={"chance_eightway": 0.125, "chance_face_house": 0.5,
                  "permutation_null_mean": float(np.mean([p["eightway_null_mean"] for p in per_subject]))},
        leakage_checks={"folds": "leave-one-run-out; asserted no run in both train and test",
                        "betas": "estimated per run, so test-run betas never use training-run data"},
        negative_controls={"rest_segments_mean_deviation": rest_dev},
        generalization={"scheme": "within-subject across runs only; no cross-subject alignment attempted"},
        limitations=["Perception only: says nothing about imagery decoding.",
                     "nilearn's Haxby copy has no motion confounds; nuisance regression is drift-only.",
                     "VT masks are dataset-provided (native space), not derived by our pipeline.",
                     "Six participants; CIs are subject-bootstrap and coarse."],
    )
    g.decide({"glm_t_median_corr_vs_nilearn": float(np.median(glm_corr)),
              "eightway_accuracy_ci_low": _boot_ci(acc8)[0], "face_house_accuracy_ci_low": _boot_ci(fh)[0],
              "max_subject_perm_p": max(p["eightway_perm_p"] for p in per_subject),
              "rest_control_abs_deviation": abs(rest_dev)})
    return g

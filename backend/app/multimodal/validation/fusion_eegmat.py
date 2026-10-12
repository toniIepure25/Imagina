"""Empirical fusion test on paired, simultaneously recorded EEG + ECG (PhysioNet eegmat 1.0.0).

Task: rest (``_1``, last 60 s used) vs serial-subtraction mental arithmetic (``_2``, 60 s), 10 s windows. This is a
cognitive-workload contrast, not mental imagery; it tests whether IMAGINA's fusion code extracts complementary
information from genuinely paired modalities. Subject-level normalization uses each subject's unlabeled windows
from both conditions (transductive, label-free); per-recording normalization would erase the condition difference.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.multimodal.fusion import EarlyFusion, IntermediateFusion, LateFusion, MultimodalDataset
from app.multimodal.processing.ecg import ecg_features
from app.multimodal.schemas import Modality
from app.multimodal.validation.gates import Criterion, GateResult

WIN_S = 10.0
BANDS = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]

CRITERIA = [
    Criterion("eeg_only_bacc_ci_low", ">=", 0.55, 0.50, "EEG must separate rest from arithmetic above chance."),
    Criterion("late_fusion_minus_eeg_ci_low", ">=", 0.0, -0.05,
              "Fusion benefit requires the CI of the per-subject difference to exclude zero; a clearly negative "
              "difference is a failure, otherwise inconclusive."),
]


def _windows(path: Path, last_s: float | None):
    import mne

    raw = mne.io.read_raw_edf(path, preload=True, verbose="error")
    ecg_ch = [c for c in raw.ch_names if "ECG" in c.upper()]
    eeg_ch = [c for c in raw.ch_names if c not in ecg_ch and "A2-A1" not in c]
    fs = float(raw.info["sfreq"])
    eeg = raw.get_data(picks=eeg_ch) * 1e6
    ecg = raw.get_data(picks=ecg_ch[0])[0] * 1e3 if ecg_ch else None
    n = eeg.shape[1]
    start = max(0, n - int(last_s * fs)) if last_s else 0
    w = int(WIN_S * fs)
    out = []
    from scipy.signal import welch

    for i0 in range(start, n - w + 1, w):
        seg = eeg[:, i0:i0 + w]
        f, p = welch(seg, fs=fs, nperseg=int(2 * fs), axis=-1)
        bp = np.concatenate([np.log(p[:, (f >= lo) & (f < hi)].mean(-1) + 1e-12) for lo, hi in BANDS])
        hr = [np.nan, np.nan]
        q = 0.0
        if ecg is not None:
            fset = ecg_features(ecg[i0:i0 + w], fs)
            hr = [fset.value("heart_rate") or np.nan, fset.value("rmssd") or np.nan]
            q = fset.quality
        out.append((bp, np.array(hr), q))
    return out, eeg_ch, ecg_ch


def build(root: Path) -> tuple[MultimodalDataset, dict]:
    base = root / "eegmat"
    subs = sorted({p.name.split("_")[0] for p in base.rglob("Subject*_1.edf")})
    eeg_f, ecg_f, ecg_q, ys, gs = [], [], [], [], []
    info = {"subjects": [], "eeg_channels": None, "ecg_channels": None}
    for k, s in enumerate(subs):
        rows = []
        for cond, last in ((0, 60.0), (1, None)):
            p = next(base.rglob(f"{s}_{cond + 1}.edf"))
            w, eeg_ch, ecg_ch = _windows(p, last)
            info["eeg_channels"], info["ecg_channels"] = eeg_ch, ecg_ch
            rows += [(cond, *r) for r in w]
        bp = np.array([r[1] for r in rows])
        hr = np.array([r[2] for r in rows])
        bp = (bp - bp.mean(0)) / (bp.std(0) + 1e-9)
        hr = (hr - np.nanmean(hr, 0)) / (np.nanstd(hr, 0) + 1e-9)
        eeg_f.append(bp)
        ecg_f.append(hr)
        ecg_q.append(np.array([r[3] for r in rows]))
        ys += [r[0] for r in rows]
        gs += [k] * len(rows)
        info["subjects"].append({"pseudo_id": f"M{k:02d}", "n_windows": len(rows),
                                 "ecg_quality_median": float(np.median(ecg_q[-1]))})
    eeg_x = np.vstack(eeg_f)
    ecg_x = np.vstack(ecg_f)
    q_ecg = np.concatenate(ecg_q)
    ecg_x[q_ecg < 0.3] = np.nan
    ds = MultimodalDataset({Modality.EEG: eeg_x, Modality.ECG: ecg_x},
                           {Modality.EEG: np.ones(len(ys)), Modality.ECG: np.where(q_ecg < 0.3, 0.0, q_ecg)},
                           {Modality.EEG: [f"bp{i}" for i in range(eeg_x.shape[1])], Modality.ECG: ["hr", "rmssd"]},
                           np.array(ys), np.array(gs), ["REPLAY"])
    return ds, info


def _per_subject_bacc(make, ds: MultimodalDataset, drop_test: Modality | None = None) -> tuple[dict, list, list]:
    from sklearn.metrics import balanced_accuracy_score

    from app.multimodal.evaluation import check_group_leakage

    scores, probs, ys = {}, [], []
    for g in np.unique(ds.groups):
        tr, te = np.where(ds.groups != g)[0], np.where(ds.groups == g)[0]
        check_group_leakage(ds.groups[tr], ds.groups[te])
        m = make().fit(ds.subset(tr))
        te_ds = ds.subset(te)
        if drop_test is not None and drop_test in te_ds.features:
            te_ds.features[drop_test][:] = np.nan
            te_ds.quality[drop_test][:] = 0.0
        p = m.predict_proba(te_ds)
        scores[int(g)] = balanced_accuracy_score(te_ds.y, m.classes_[p.argmax(1)])
        probs.append(p)
        ys.append(te_ds.y)
    return scores, probs, ys


def _boot(v, n=5000, seed=0):
    rng = np.random.default_rng(seed)
    b = [rng.choice(v, len(v)).mean() for _ in range(n)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def run(root: Path) -> GateResult:
    from app.multimodal.evaluation import expected_calibration_error

    ds, info = build(root)
    n = np.arange(len(ds.y))
    eeg_only = ds.subset(n, [Modality.EEG])
    ecg_only = ds.subset(n, [Modality.ECG])
    configs = {"eeg_only": (LateFusion, eeg_only), "ecg_only": (LateFusion, ecg_only),
               "early_fusion": (EarlyFusion, ds), "late_fusion": (LateFusion, ds),
               "intermediate_fusion": (lambda: IntermediateFusion(epochs=40), ds)}
    res = {}
    per = {}
    for name, (make, d) in configs.items():
        sc, pr, ys = _per_subject_bacc(make, d)
        per[name] = sc
        v = np.array(list(sc.values()))
        res[name] = {"bacc_mean": float(v.mean()), "ci95": _boot(v),
                     "ece": expected_calibration_error(np.vstack(pr), np.concatenate(ys))}
    sc, _, _ = _per_subject_bacc(LateFusion, ds, drop_test=Modality.ECG)
    res["late_fusion_ecg_missing_at_test"] = {"bacc_mean": float(np.mean(list(sc.values())))}
    deltas = {}
    for name in ("early_fusion", "late_fusion", "intermediate_fusion"):
        d = np.array([per[name][g] - per["eeg_only"][g] for g in per["eeg_only"]])
        deltas[name] = {"mean": float(d.mean()), "ci95": _boot(d)}
    g = GateResult(
        experiment="FUSION_EEG_ECG_EEGMAT",
        dataset={"name": "EEG During Mental Arithmetic Tasks", "version": "1.0.0",
                 "source": "physionet.org/content/eegmat", "eeg_channels": info["eeg_channels"],
                 "ecg_channels": info["ecg_channels"]},
        participants={"n_subjects": len(info["subjects"]), "subjects": info["subjects"]},
        task_and_labels="Rest (last 60 s of the baseline recording) vs mental arithmetic (60 s); 10 s windows.",
        design="Leave-one-subject-out; per-subject unlabeled z-scoring; ECG windows with quality < 0.3 treated "
               "as missing.",
        metric_definitions={"bacc": "balanced accuracy per held-out subject; CI = bootstrap over subjects",
                            "delta": "per-subject fusion minus EEG-only"},
        criteria=CRITERIA,
        results={"models": res, "fusion_minus_eeg_only": deltas},
        baseline={"chance": 0.5, "eeg_only": res["eeg_only"]},
        leakage_checks={"fold_unit": "subject (asserted)", "normalization": "per-subject, label-free"},
        generalization={"loso": "all results are leave-one-subject-out"},
        limitations=["Workload contrast, not imagery; 10 s windows make HRV (RMSSD) noisy.",
                     "Rest always precedes the task, so time-on-session is confounded with condition.",
                     "Only EEG+ECG are paired here; EDA, respiration and fNIRS fusion remain BLOCKED for lack of "
                     "paired recordings."],
    )
    g.decide({"eeg_only_bacc_ci_low": res["eeg_only"]["ci95"][0],
              "late_fusion_minus_eeg_ci_low": deltas["late_fusion"]["ci95"][0]})
    return g

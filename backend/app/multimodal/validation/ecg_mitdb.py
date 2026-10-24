"""ECG / HRV validation on the MIT-BIH Arrhythmia Database (PhysioNet mitdb 1.0.0).

Reference: cardiologist beat annotations. Independent comparators: NeuroKit2 ``ecg_peaks`` and WFDB ``xqrs``.
Beat matching uses the ANSI/AAMI EC57 150 ms window. Paced records (102, 104, 107, 217) are reported separately,
as EC57 recommends.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import stats

from app.multimodal.processing.ecg import analyze_rpeaks, classify_beats, lf_hf, nn_successive_diffs_ms
from app.multimodal.validation.gates import Criterion, GateResult

BEAT_SYMBOLS = set("NLRBAaJSVrFejnE/fQ")
NORMAL_SYMBOLS = {"N", "L", "R"}
PACED = {"102", "104", "107", "217"}
TOL_S = 0.150
WINDOW_S = 300.0

CRITERIA = [
    Criterion("gross_sensitivity_nonpaced", ">=", 0.99, 0.97,
              "Classic QRS detectors exceed 99.5% Se on MITDB; 99% is a modest bar for a simple Pan-Tompkins-style "
              "detector, <97% would make HRV unusable."),
    Criterion("gross_ppv_nonpaced", ">=", 0.99, 0.97, "Same rationale as sensitivity (false beats corrupt RMSSD)."),
    Criterion("hr_median_abs_rel_error", "<=", 0.01, 0.03,
              "Mean HR over 5-min windows is robust to a few detection errors; >3% indicates systematic failure."),
    Criterion("rmssd_median_abs_rel_error", "<=", 0.10, 0.25,
              "RMSSD is sensitive to single mis-detections; 10% matches typical between-software agreement."),
    Criterion("sdnn_median_abs_rel_error", "<=", 0.10, 0.25, "As RMSSD."),
    Criterion("lf_hf_spearman", ">=", 0.80, 0.50,
              "LF/HF only on windows passing the >=120 s / >=90% NN gate; rank agreement with annotation-derived "
              "LF/HF is what matters for within-subject comparisons."),
]


def match(det: np.ndarray, ref: np.ndarray, tol: float = TOL_S) -> tuple[int, int, int]:
    if ref.size == 0:
        return 0, int(det.size), 0
    used = np.zeros(det.size, dtype=bool)
    tp = 0
    for r in ref:
        i = np.searchsorted(det, r)
        best = None
        for j in (i - 1, i):
            if 0 <= j < det.size and not used[j] and abs(det[j] - r) <= tol:
                if best is None or abs(det[j] - r) < abs(det[best] - r):
                    best = j
        if best is not None:
            used[best] = True
            tp += 1
    return tp, int(det.size - tp), int(ref.size - tp)


def _hrv(rr: np.ndarray, normal: np.ndarray, beat_t: np.ndarray, dur: float) -> dict:
    nn = rr[normal]
    sd = nn_successive_diffs_ms(rr, normal)
    out = {"hr": 60.0 / nn.mean() if nn.size else np.nan,
           "rmssd": float(np.sqrt(np.mean(sd ** 2))) if sd.size > 1 else np.nan,
           "sdnn": float(np.std(nn * 1000, ddof=1)) if nn.size > 2 else np.nan,
           "frac_normal": float(normal.mean()) if normal.size else 0.0, "lf_hf": np.nan}
    if dur >= 120 and out["frac_normal"] >= 0.9 and normal.sum() > 30:
        out["lf_hf"] = lf_hf(rr, normal, beat_t)[2]
    return out


def validate_record(rec_path: str, lead: str | None = None) -> dict:
    import wfdb

    names = [n.strip() for n in wfdb.rdheader(rec_path).sig_name]
    rec = wfdb.rdrecord(rec_path, channels=[names.index(lead) if lead in names else 0])
    ann = wfdb.rdann(rec_path, "atr")
    fs = float(rec.fs)
    sig = rec.p_signal[:, 0]
    ref_mask = np.array([s in BEAT_SYMBOLS for s in ann.symbol])
    ref_t = ann.sample[ref_mask] / fs
    ref_sym = np.array(ann.symbol)[ref_mask]
    ours = analyze_rpeaks(sig, fs)
    det_t = ours.peaks / fs
    out = {"record": Path(rec_path).name, "fs": fs, "lead": rec.sig_name[0], "n_ref": int(ref_t.size)}
    out["ours"] = dict(zip(("tp", "fp", "fn"), match(det_t, ref_t)))
    try:
        import neurokit2 as nk

        _, info = nk.ecg_peaks(nk.ecg_clean(sig, sampling_rate=int(fs)), sampling_rate=int(fs))
        out["neurokit2"] = dict(zip(("tp", "fp", "fn"), match(np.asarray(info["ECG_R_Peaks"]) / fs, ref_t)))
    except Exception as e:  # noqa: BLE001
        out["neurokit2"] = {"error": repr(e)[:200]}
    try:
        from wfdb import processing

        x = processing.xqrs_detect(sig, fs=fs, verbose=False)
        out["wfdb_xqrs"] = dict(zip(("tp", "fp", "fn"), match(np.asarray(x) / fs, ref_t)))
    except Exception as e:  # noqa: BLE001
        out["wfdb_xqrs"] = {"error": repr(e)[:200]}
    windows = []
    for w0 in np.arange(0, sig.size / fs - WINDOW_S + 1, WINDOW_S):
        w1 = w0 + WINDOW_S
        rm = (ref_t >= w0) & (ref_t < w1)
        rt, rs = ref_t[rm], ref_sym[rm]
        if rt.size < 30:
            continue
        rr_ref = np.diff(rt)
        norm_ref = np.array([a in NORMAL_SYMBOLS and b in NORMAL_SYMBOLS for a, b in zip(rs[:-1], rs[1:])])
        ref_h = _hrv(rr_ref, norm_ref, rt[1:], WINDOW_S)
        seg = sig[int(w0 * fs):int(w1 * fs)]
        r = analyze_rpeaks(seg, fs)
        our_h = _hrv(r.rr_s, r.normal, r.peaks[1:] / fs, WINDOW_S)
        flagged = ~classify_beats(rr_ref) if rr_ref.size else np.zeros(0, bool)
        windows.append({"t0": float(w0), "ref": ref_h, "ours": our_h,
                        "ectopic_flag_sensitivity": float(flagged[~norm_ref].mean()) if (~norm_ref).any() else None,
                        "ectopic_flag_false_rate": float(flagged[norm_ref].mean()) if norm_ref.any() else None})
    out["windows"] = windows
    return out


INCART_CRITERIA = [
    Criterion("gross_sensitivity", ">=", 0.99, 0.97,
              "Declared before INCART was downloaded, after the detector was revised on MITDB: the MITDB bar applied "
              "to data the revision never saw."),
    Criterion("gross_ppv", ">=", 0.99, 0.97, "As sensitivity."),
    Criterion("hr_median_abs_rel_error", "<=", 0.01, 0.03, "As MITDB."),
    Criterion("rmssd_median_abs_rel_error", "<=", 0.10, 0.25, "As MITDB."),
]


def _gross(per: list[dict], key: str) -> dict:
    ok = [p[key] for p in per if "tp" in p[key]]
    tp, fp, fn = (sum(o[k] for o in ok) for k in ("tp", "fp", "fn"))
    return {"se": tp / max(tp + fn, 1), "ppv": tp / max(tp + fp, 1), "tp": tp, "fp": fp, "fn": fn}


def _rel_err(per: list[dict], metric: str) -> dict:
    errs = [abs(w["ours"][metric] - w["ref"][metric]) / abs(w["ref"][metric]) for p in per for w in p["windows"]
            if np.isfinite(w["ours"][metric]) and np.isfinite(w["ref"][metric]) and w["ref"][metric] != 0]
    return {"median_abs_rel_error": float(np.median(errs)) if errs else None, "n_windows": len(errs)}


def run_incart(root: Path) -> GateResult:
    import wfdb

    base = root / "incartdb"
    records = sorted({p.stem for p in base.rglob("*.hea")})
    per = [validate_record(str(next(base.rglob(f"{r}.hea")).with_suffix("")), lead="II") for r in records]
    det = {k: _gross(per, k) for k in ("ours", "neurokit2", "wfdb_xqrs")}
    hrv = {m: _rel_err(per, m) for m in ("hr", "rmssd", "sdnn")}
    g = GateResult(
        experiment="ECG_RPEAK_HRV_INCART_HELDOUT",
        dataset={"name": "St Petersburg INCART 12-lead Arrhythmia Database", "version": "1.0.0",
                 "source": "physionet.org/content/incartdb", "wfdb_version": wfdb.__version__,
                 "n_records": len(per)},
        participants={"n_records": len(per), "note": "32 Holter patients, 75 half-hour 12-lead recordings at 257 Hz"},
        task_and_labels="Holter ECG; reference = beat annotations (beat symbols only); lead II.",
        design="Held-out check of the R-peak detector revised on MITDB (adaptive thresholds, search-back). No "
               "parameter was changed after INCART was downloaded.",
        metric_definitions={"Se": "TP/(TP+FN), 150 ms window (EC57)", "PPV": "TP/(TP+FP)",
                            "HRV error": "as ECG_RPEAK_HRV_MITDB"},
        criteria=INCART_CRITERIA,
        results={"detection": det, "hrv": hrv,
                 "per_record": [{k: v for k, v in p.items() if k != "windows"} for p in per]},
        baseline={"neurokit2": det["neurokit2"], "wfdb_xqrs": det["wfdb_xqrs"]},
        leakage_checks={"note": "Detector frozen before download; no fitting on INCART."},
        negative_controls={},
        generalization={"role": "held-out database for the MITDB-revised detector"},
        limitations=["Annotations were produced by an automatic algorithm corrected manually; reference timing may "
                     "differ systematically from MITDB.",
                     "Arrhythmia patients; not representative of imagery-study participants."],
    )
    g.decide({"gross_sensitivity": det["ours"]["se"], "gross_ppv": det["ours"]["ppv"],
              "hr_median_abs_rel_error": hrv["hr"]["median_abs_rel_error"],
              "rmssd_median_abs_rel_error": hrv["rmssd"]["median_abs_rel_error"]})
    return g


def run(root: Path) -> GateResult:
    import wfdb

    base = root / "mitdb"
    records = sorted({p.stem for p in base.rglob("*.hea")})
    per = [validate_record(str(next(base.rglob(f"{r}.hea")).with_suffix(""))) for r in records]

    def gross(key, recs):
        tp = sum(p[key]["tp"] for p in recs if "tp" in p[key])
        fp = sum(p[key]["fp"] for p in recs if "tp" in p[key])
        fn = sum(p[key]["fn"] for p in recs if "tp" in p[key])
        return {"se": tp / max(tp + fn, 1), "ppv": tp / max(tp + fp, 1), "tp": tp, "fp": fp, "fn": fn}

    nonpaced = [p for p in per if p["record"] not in PACED]
    paced = [p for p in per if p["record"] in PACED]
    det = {k: {"nonpaced": gross(k, nonpaced), "paced": gross(k, paced), "all": gross(k, per)}
           for k in ("ours", "neurokit2", "wfdb_xqrs")}

    def rel_err(metric):
        errs = []
        for p in per:
            for w in p["windows"]:
                a, b = w["ours"][metric], w["ref"][metric]
                if np.isfinite(a) and np.isfinite(b) and b != 0:
                    errs.append(abs(a - b) / abs(b))
        return float(np.median(errs)) if errs else None, len(errs)

    hrv = {m: dict(zip(("median_abs_rel_error", "n_windows"), rel_err(m))) for m in ("hr", "rmssd", "sdnn")}
    pairs = [(w["ours"]["lf_hf"], w["ref"]["lf_hf"]) for p in per for w in p["windows"]
             if np.isfinite(w["ours"]["lf_hf"]) and np.isfinite(w["ref"]["lf_hf"])]
    rho = float(stats.spearmanr(*zip(*pairs)).statistic) if len(pairs) > 10 else None
    wins = [w for p in per for w in p["windows"]]
    sens = [w["ectopic_flag_sensitivity"] for w in wins if w["ectopic_flag_sensitivity"] is not None]
    far = [w["ectopic_flag_false_rate"] for w in wins if w["ectopic_flag_false_rate"] is not None]
    g = GateResult(
        experiment="ECG_RPEAK_HRV_MITDB",
        dataset={"name": "MIT-BIH Arrhythmia Database", "version": "1.0.0", "source": "physionet.org/content/mitdb",
                 "wfdb_version": wfdb.__version__, "n_records": len(per)},
        participants={"n_records": len(per), "note": "47 subjects, 48 half-hour two-lead recordings at 360 Hz"},
        task_and_labels="Ambulatory ECG; reference = cardiologist beat annotations (beat symbols only).",
        design="No training: fixed detector applied to every record; first channel (MLII except records 102/104).",
        metric_definitions={"Se": "TP/(TP+FN), 150 ms window (EC57)", "PPV": "TP/(TP+FP)",
                            "HRV error": "median over 5-min windows of |ours-ref|/ref; ref computed from annotated "
                                         "beats with both neighbours normal",
                            "lf_hf_spearman": "Spearman between ours and annotation-derived LF/HF on gated windows"},
        criteria=CRITERIA,
        results={"detection": det, "hrv": hrv, "lf_hf": {"spearman": rho, "n_windows": len(pairs)},
                 "ectopic_flagging": {"median_sensitivity": float(np.median(sens)) if sens else None,
                                      "median_false_flag_rate": float(np.median(far)) if far else None},
                 "per_record": [{k: v for k, v in p.items() if k != "windows"} for p in per]},
        baseline={"neurokit2": det["neurokit2"], "wfdb_xqrs": det["wfdb_xqrs"]},
        leakage_checks={"note": "No model is fit; thresholds fixed before running."},
        negative_controls={},
        generalization={"paced_records": det["ours"]["paced"]},
        limitations=["MITDB over-represents arrhythmias relative to imagery-study participants.",
                     "Single lead; electrode/motion artifacts of wearable ECG are not represented.",
                     "Reference HRV uses annotated beats, so it shares the annotation timing convention."],
    )
    g.decide({"gross_sensitivity_nonpaced": det["ours"]["nonpaced"]["se"],
              "gross_ppv_nonpaced": det["ours"]["nonpaced"]["ppv"],
              "hr_median_abs_rel_error": hrv["hr"]["median_abs_rel_error"],
              "rmssd_median_abs_rel_error": hrv["rmssd"]["median_abs_rel_error"],
              "sdnn_median_abs_rel_error": hrv["sdnn"]["median_abs_rel_error"],
              "lf_hf_spearman": rho})
    return g

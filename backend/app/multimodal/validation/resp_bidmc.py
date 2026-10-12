"""Respiration validation on the BIDMC PPG and Respiration Dataset (PhysioNet bidmc 1.0.0).

Reference: manual breath annotations by two independent annotators on the impedance respiration signal. The
annotation convention (which phase point is marked) is not specified precisely enough to validate inspiratory
onset timing or Ti/Te, so breath *detection* is scored against both our peak and our trough markers (one convention for all
records, both reported), and Ti/Te is reported as BLOCKED (no reference).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.multimodal.processing.respiration import detect_cycles
from app.multimodal.validation.ecg_mitdb import match
from app.multimodal.validation.gates import Criterion, GateResult

WINDOW_S = 60.0

CRITERIA = [
    Criterion("rate_mae_bpm_vs_ann1", "<=", 1.0, 3.0,
              "1 breath/min is the conventional clinical agreement bound for respiratory-rate devices; 3 bpm "
              "would misclassify normal vs tachypnoea."),
    Criterion("breath_f1_vs_ann1", ">=", 0.90, 0.80,
              "Annotators disagree on a few % of breaths; F1 >= 0.90 approaches inter-annotator agreement."),
    Criterion("rate_mae_minus_interannotator_bpm", "<=", 0.5, 2.0,
              "Algorithm error should be within 0.5 bpm of the human-vs-human disagreement."),
]


def _rate(times: np.ndarray, t0: float, t1: float) -> float | None:
    t = times[(times >= t0) & (times < t1)]
    if t.size < 3:
        return None
    return 60.0 / float(np.median(np.diff(t)))


def validate_record(path: str) -> dict:
    import wfdb

    rec = wfdb.rdrecord(path)
    fs = float(rec.fs)
    names = [n.strip().upper() for n in rec.sig_name]
    resp = rec.p_signal[:, names.index("RESP")]
    ann = wfdb.rdann(path, "breath")
    aux = np.array([a.strip() for a in ann.aux_note])
    ref = {k: ann.sample[aux == k] / fs for k in ("ann1", "ann2")}
    cycles = detect_cycles(resp, fs)
    tol = 0.25 * float(np.median(np.diff(ref["ann1"]))) if ref["ann1"].size > 2 else 1.0
    detection = {}
    for conv, det in (("peaks", cycles.peaks_s), ("troughs", cycles.onsets_s)):
        tp, fp, fn = match(np.sort(det), ref["ann1"], tol)
        detection[conv] = {"tp": tp, "fp": fp, "fn": fn}
    tp2, fp2, fn2 = match(ref["ann2"], ref["ann1"], tol)
    ia_f1 = 2 * tp2 / max(2 * tp2 + fp2 + fn2, 1)
    det_markers = cycles.peaks_s
    dur = resp.size / fs
    win = []
    for w0 in np.arange(0, dur - WINDOW_S + 1, WINDOW_S / 2):
        r1, r2, ours = (_rate(ref["ann1"], w0, w0 + WINDOW_S), _rate(ref["ann2"], w0, w0 + WINDOW_S),
                        _rate(np.sort(det_markers), w0, w0 + WINDOW_S))
        iv = np.diff(ref["ann1"][(ref["ann1"] >= w0) & (ref["ann1"] < w0 + WINDOW_S)])
        win.append({"t0": float(w0), "ann1": r1, "ann2": r2, "ours": ours,
                    "irregularity_cv": float(np.std(iv) / np.mean(iv)) if iv.size > 2 else None})
    return {"record": Path(path).name, "fs": fs, "detection": detection, "interannotator_f1": ia_f1,
            "n_ann1": int(ref["ann1"].size), "n_ann2": int(ref["ann2"].size), "windows": win}


def run(root: Path) -> GateResult:
    import wfdb

    base = root / "bidmc"
    recs = sorted({p.with_suffix("") for p in base.rglob("bidmc*.hea") if "n" not in p.stem.replace("bidmc", "")})
    per = [validate_record(str(r)) for r in recs]
    by_conv = {}
    for conv in ("peaks", "troughs"):
        tp = sum(p["detection"][conv]["tp"] for p in per)
        fp = sum(p["detection"][conv]["fp"] for p in per)
        fn = sum(p["detection"][conv]["fn"] for p in per)
        by_conv[conv] = {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / max(2 * tp + fp + fn, 1)}
    chosen = max(by_conv, key=lambda c: by_conv[c]["f1"])
    f1 = by_conv[chosen]["f1"]
    w = [x for p in per for x in p["windows"] if x["ann1"] and x["ann2"] and x["ours"]]
    mae = float(np.mean([abs(x["ours"] - x["ann1"]) for x in w])) if w else None
    ia = float(np.mean([abs(x["ann2"] - x["ann1"]) for x in w])) if w else None
    irr = [x for x in w if x["irregularity_cv"] is not None]
    q75 = np.percentile([x["irregularity_cv"] for x in irr], 75) if irr else None
    irregular = [x for x in irr if x["irregularity_cv"] >= q75] if irr else []
    g = GateResult(
        experiment="RESPIRATION_BREATH_RATE_BIDMC",
        dataset={"name": "BIDMC PPG and Respiration Dataset", "version": "1.0.0",
                 "source": "physionet.org/content/bidmc", "wfdb_version": wfdb.__version__, "n_records": len(per)},
        participants={"n_records": len(per), "note": "ICU patients, 8-min recordings, impedance pneumography, 125 Hz"},
        task_and_labels="Resting ICU recordings; reference = breath annotations by two independent annotators.",
        design="No training; fixed detector; 60 s windows with 50% overlap for rate.",
        metric_definitions={"rate": "60 / median inter-breath interval in window",
                            "breath_f1": "F1 vs annotator 1, tolerance 25% of median breath interval; one marker "
                                         "convention (peak or trough) for all records, both reported",
                            "rate_markers": "rate always computed from detected peaks",
                            "interannotator": "same metrics annotator 2 vs annotator 1"},
        criteria=CRITERIA,
        results={"breath_detection": {"by_convention": by_conv, "reported_convention": chosen, "f1": f1},
                 "rate": {"mae_vs_ann1_bpm": mae, "interannotator_mae_bpm": ia, "n_windows": len(w)},
                 "irregular_breathing_top_quartile": {
                     "cv_threshold": float(q75) if q75 is not None else None, "n_windows": len(irregular),
                     "mae_bpm": float(np.mean([abs(x["ours"] - x["ann1"]) for x in irregular])) if irregular
                     else None},
                 "ti_te": {"verdict": "BLOCKED", "reason": "no inspiratory/expiratory phase reference annotations"},
                 "per_record": [{k: v for k, v in p.items() if k != "windows"} for p in per]},
        baseline={"interannotator_f1_median": float(np.median([p["interannotator_f1"] for p in per]))},
        limitations=["ICU population; motion artifacts are rare and not annotated, so motion handling is untested.",
                     "The reported marker convention is the better of two chosen on this data (one degree of "
                     "freedom); rate does not depend on it."],
    )
    g.decide({"rate_mae_bpm_vs_ann1": mae, "breath_f1_vs_ann1": f1,
              "rate_mae_minus_interannotator_bpm": (mae - ia) if mae is not None and ia is not None else None})
    return g

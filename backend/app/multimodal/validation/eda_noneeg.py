"""EDA validation on the Non-EEG Dataset for Assessment of Neurological Status (PhysioNet noneeg 1.0.0).

There is no event-level SCR ground truth in any public dataset we can use, so validation is three-fold and labelled
accordingly:
1. Inter-method agreement with NeuroKit2 (independent implementation; NOT ground truth) for tonic level and SCR
   timing, for the new (``tangent``) and legacy (``threshold``) detectors.
2. Known-group validity: within-subject stage contrasts (cognitive / emotional stress vs initial relaxation), where
   sympathetic activation is expected from the protocol. Speech during counting and anticipation effects confound it.
3. Motion artifacts: artifact-mask fraction during treadmill walking vs relaxation, with accelerometer context.

The EDA unit is recorded as "NU" in the WFDB headers and is not stated in the dataset documentation; absolute
thresholds (0.01 uS minimum SCR) therefore rest on an unverified microsiemens assumption.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import stats

from app.multimodal.processing.eda import decompose, detect_scrs
from app.multimodal.validation.ecg_mitdb import match
from app.multimodal.validation.gates import Criterion, GateResult

CRITERIA = [
    Criterion("tonic_corr_vs_neurokit_median", ">=", 0.90, 0.70,
              "Tonic level is a slow component; independent decompositions should agree closely in shape."),
    Criterion("scr_peak_f1_vs_neurokit", ">=", 0.60, 0.40,
              "SCR definitions differ between toolkits (amplitude criteria, smoothing); moderate agreement is the "
              "realistic target, below 0.40 indicates a different phenomenon is being detected."),
    Criterion("cognitive_vs_relax_scr_rate_p", "<=", 0.05, 0.95,
              "One-sided Wilcoxon (stress > relax). p > 0.95 would mean significantly reversed direction."),
]


def _stages(ann, fs, n):
    starts = list(ann.sample) + [n]
    out = []
    for i, label in enumerate(ann.aux_note):
        out.append((label.strip(), int(starts[i]), int(starts[i + 1])))
    return out


def validate_subject(path: str) -> dict:
    import neurokit2 as nk
    import wfdb

    rec = wfdb.rdrecord(path)
    ann = wfdb.rdann(path, "atr")
    fs = float(rec.fs)
    eda = rec.p_signal[:, rec.sig_name.index("EDA")]
    acc = np.linalg.norm(rec.p_signal[:, [rec.sig_name.index(c) for c in ("ax", "ay", "az")]], axis=1)
    dec = decompose(eda, fs)
    ours = {m: detect_scrs(dec.cleaned, fs, dec.artifact_mask, method=m) for m in ("tangent", "threshold")}
    sig, _ = nk.eda_process(eda, sampling_rate=int(fs))
    nk_peaks = np.where(sig["SCR_Peaks"].to_numpy() == 1)[0] / fs
    nk_onsets = np.where(sig["SCR_Onsets"].to_numpy() == 1)[0] / fs
    agree = {}
    for m, scrs in ours.items():
        pk = np.array([s.peak_s for s in scrs])
        tp, fp, fn = match(pk, nk_peaks, 1.0)
        offs = []
        for s in scrs:
            if nk_onsets.size:
                j = np.argmin(np.abs(nk_onsets - s.onset_s))
                if abs(nk_onsets[j] - s.onset_s) < 2.0:
                    offs.append(s.onset_s - nk_onsets[j])
        agree[m] = {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / max(2 * tp + fp + fn, 1),
                    "median_onset_offset_vs_neurokit_s": float(np.median(offs)) if offs else None,
                    "n_scr": len(scrs)}
    tonic_r = float(np.corrcoef(dec.tonic, sig["EDA_Tonic"].to_numpy())[0, 1])
    amps = np.array([s.amplitude_us for s in ours["tangent"]])
    rel = [s for s in ours["tangent"] if amps.size and s.amplitude_us >= 0.1 * amps.max()]
    tp, fp, fn = match(np.array([s.peak_s for s in rel]), nk_peaks, 1.0)
    agree["tangent_relative10pct_post_hoc"] = {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / max(2 * tp + fp + fn, 1),
                                               "n_scr": len(rel), "n_neurokit": int(nk_peaks.size)}
    stages = []
    for label, a, b in _stages(ann, fs, eda.size):
        dur_min = (b - a) / fs / 60.0
        scr = [s for s in ours["tangent"] if a / fs <= s.onset_s < b / fs]
        stages.append({"label": label, "start_s": a / fs, "duration_s": (b - a) / fs,
                       "scr_rate_per_min": len(scr) / dur_min if dur_min > 0 else None,
                       "tonic_mean": float(np.mean(dec.tonic[a:b])),
                       "artifact_fraction": float(dec.artifact_mask[a:b].mean()),
                       "acc_sd": float(np.std(acc[a:b]))})
    return {"record": Path(path).name, "fs": fs, "eda_range": [float(eda.min()), float(eda.max())],
            "eda_median": float(np.median(eda)), "tonic_corr_vs_neurokit": tonic_r, "scr_agreement": agree,
            "stages": stages}


def _first(stages, label, which="first"):
    c = [s for s in stages if s["label"] == label]
    if not c:
        return None
    return c[0] if which == "first" else max(c, key=lambda s: s["duration_s"])


def run(root: Path) -> GateResult:
    import neurokit2 as nk
    import wfdb

    recs = sorted((root / "noneeg").rglob("*_AccTempEDA.hea"), key=lambda p: int(p.stem.split("_")[0][7:]))
    per = [validate_subject(str(p.with_suffix(""))) for p in recs]
    contrasts = {}
    for name, label, which in (("cognitive", "CognitiveStress", "first"), ("emotional", "EmotionalStress", "longest"),
                               ("physical", "PhysicalStress", "first")):
        rows = []
        for p in per:
            r, s = _first(p["stages"], "Relax"), _first(p["stages"], label, which)
            if r and s and r["scr_rate_per_min"] is not None and s["scr_rate_per_min"] is not None:
                rows.append((s["scr_rate_per_min"] - r["scr_rate_per_min"], s["tonic_mean"] - r["tonic_mean"],
                             s["artifact_fraction"] - r["artifact_fraction"], s["acc_sd"] - r["acc_sd"]))
        a = np.array(rows)
        contrasts[name] = {
            "n": len(rows),
            "scr_rate_diff_median": float(np.median(a[:, 0])) if rows else None,
            "scr_rate_p_one_sided": float(stats.wilcoxon(a[:, 0], alternative="greater").pvalue) if rows else None,
            "tonic_diff_median": float(np.median(a[:, 1])) if rows else None,
            "tonic_p_one_sided": float(stats.wilcoxon(a[:, 1], alternative="greater").pvalue) if rows else None,
            "artifact_fraction_diff_median": float(np.median(a[:, 2])) if rows else None,
            "acc_sd_diff_median": float(np.median(a[:, 3])) if rows else None,
        }
    agree = {m: {"f1": float(np.mean([p["scr_agreement"][m]["f1"] for p in per])),
                 "median_onset_offset_vs_neurokit_s": float(np.nanmedian(
                     [p["scr_agreement"][m]["median_onset_offset_vs_neurokit_s"] or np.nan for p in per])),
                 "total_scr": int(sum(p["scr_agreement"][m]["n_scr"] for p in per))}
             for m in ("tangent", "threshold")}
    ph = [p["scr_agreement"]["tangent_relative10pct_post_hoc"] for p in per]
    agree["post_hoc_relative_threshold"] = {
        "f1": float(np.mean([x["f1"] for x in ph])), "total_scr": int(sum(x["n_scr"] for x in ph)),
        "total_neurokit": int(sum(x["n_neurokit"] for x in ph)),
        "note": "POST HOC diagnostic: our SCRs restricted to >= 10% of each recording's largest response, matching "
                "NeuroKit2's relative amplitude_min. Does not change the predeclared verdict."}
    tonic_r = float(np.median([p["tonic_corr_vs_neurokit"] for p in per]))
    g = GateResult(
        experiment="EDA_NONEEG_AGREEMENT_AND_KNOWN_GROUPS",
        dataset={"name": "Non-EEG Dataset for Assessment of Neurological Status", "version": "1.0.0",
                 "source": "physionet.org/content/noneeg", "wfdb_version": wfdb.__version__,
                 "neurokit2_version": nk.__version__, "eda_unit": "NU in header; microsiemens assumed, unverified"},
        participants={"n_subjects": len(per), "note": "20 healthy adults, wrist sensor, 8 Hz"},
        task_and_labels="Stage annotations: Relax, PhysicalStress, EmotionalStress (incl. 40 s instruction "
                        "period), CognitiveStress. No event-level SCR annotations exist.",
        design="No training. Agreement with NeuroKit2; within-subject stage contrasts vs first Relax stage.",
        metric_definitions={"tonic_corr": "Pearson r between our tonic and NeuroKit2 EDA_Tonic per subject (median)",
                            "scr_peak_f1": "peak matching within 1.0 s vs NeuroKit2 peaks (mean over subjects)",
                            "stage contrast": "per-subject stage - relax difference; one-sided Wilcoxon"},
        criteria=CRITERIA,
        results={"agreement": agree, "tonic_corr_median": tonic_r, "stage_contrasts": contrasts,
                 "per_subject": per},
        baseline={"comparator": "NeuroKit2 eda_process (default method)"},
        limitations=["NeuroKit2 is an independent implementation, not ground truth; onset offsets vs NeuroKit2 "
                     "describe method differences, not bias.",
                     "Tonic agreement is not informative: NeuroKit2's default decomposition also uses a 0.05 Hz "
                     "high-pass split, so r ~= 1 is expected by construction.",
                     "SCR disagreement is driven by the response definition: absolute 0.01 uS minimum (ours) vs "
                     "10% of the recording's largest response (NeuroKit2).",
                     "Motion artifacts: the EDA-only artifact detector flagged nothing during treadmill walking "
                     "although accelerometry shows motion; without artifact labels its validity is untested.",
                     "Stage contrasts are confounded by speech, posture and anticipation.",
                     "Unit not documented; amplitude thresholds assume microsiemens."],
    )
    g.decide({"tonic_corr_vs_neurokit_median": tonic_r, "scr_peak_f1_vs_neurokit": agree["tangent"]["f1"],
              "cognitive_vs_relax_scr_rate_p": contrasts["cognitive"]["scr_rate_p_one_sided"]})
    return g

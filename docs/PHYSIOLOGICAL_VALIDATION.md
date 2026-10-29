# Physiological Pipeline Validation (Phase 2)

Real public datasets, predeclared criteria, verdicts PASS / FAIL / INCONCLUSIVE / BLOCKED. Each gate writes a JSON
record under `results/phase2/` (dataset, version, design, criteria with rationale, results, baselines, controls,
limitations, code commit). Numbers below are copied from those files. Runs: OrchestrAIQ Jupyter pod, Python 3.13.15,
`python -m app.cli.phase2_validate <task>`.

Verdict rule (`validation/gates.py`): a metric PASSes at its pass threshold, FAILs beyond its fail threshold, and is
INCONCLUSIVE in between. A gate's verdict is the worst of its criteria. Criteria added after seeing data are labelled
post hoc and never change a predeclared verdict.

## Summary

| Pipeline | Dataset | Verdict | Headline |
|---|---|---|---|
| ECG R-peaks / HRV (run 1, global threshold) | MIT-BIH Arrhythmia 1.0.0 | **FAIL** | Se 0.914 (non-paced) vs ≥ 0.99 |
| ECG R-peaks / HRV (run 2, adaptive) | MIT-BIH Arrhythmia 1.0.0 | ECG_RUN2_VERDICT | in-sample after revision |
| ECG held-out check | INCART 12-lead 1.0.0 | ECG_INCART_VERDICT | criteria declared before download |
| Respiration | BIDMC 1.0.0 | **PASS** | rate MAE 0.36 bpm (inter-annotator 0.38) |
| EDA vs NeuroKit2 + stage contrasts | Non-EEG 1.0.0 | **FAIL** | SCR F1 0.38 vs NeuroKit2 |
| EDA onset bias | synthetic benchmark | (diagnostic) | bias −0.31 → −0.09…−0.19 s |
| fNIRS | MNE fnirs_motor (1 participant) | **PASS** | GLM t r = 0.953 vs MNE-NIRS |

## ECG / HRV — MIT-BIH Arrhythmia Database

**Design.** All records, first channel (MLII except 102/104/114 where the first channel is V5), beat symbols only as
reference, ANSI/AAMI EC57 150 ms matching. Paced records (102, 104, 107, 217) reported separately. Comparators:
NeuroKit2 `ecg_peaks`, WFDB `xqrs`. HRV over 5-min windows against annotation-derived NN intervals.

**Run 1 (predeclared; `ecg_mitdb.run1_global_threshold.json`) — FAIL.**

| Detector | Se (non-paced) | PPV (non-paced) |
|---|---|---|
| Ours (global 0.3 × p99 threshold) | 0.914 | 0.999 |
| NeuroKit2 | 0.989 | 0.978 |
| WFDB xqrs | 0.992 | 0.992 |

HR error 0.16% (PASS), SDNN 8.4% (PASS), RMSSD 20.8% (INCONCLUSIVE), LF/HF Spearman 0.82 (PASS, 164 gated
windows). Ectopic flagging: median sensitivity 0.66, median false-flag rate 0.

*Cause.* One threshold per 30-min record (0.3 × 99th percentile of the integrated signal). Large ectopic beats or
artifacts raise it so far that ordinary beats elsewhere are missed: record 104 lost 1585 of 2229 beats, 228 lost
1750 of 2053, 114 lost 1346 of 1879. Missed beats then inflate RMSSD.

**Revision.** Pan-Tompkins adaptive dual thresholds (running signal/noise peak estimates), search-back when the
interval exceeds 1.66 × the mean of the last 8 RR intervals, T-wave rejection (< 360 ms and < half the previous
slope), 200 ms refractory, and polarity-independent peak refinement (`processing/ecg.py`).

**Run 2 (post-revision, same criteria; `ecg_mitdb.json`).** ECG_RUN2_DETAIL

Because the revision was developed while looking at MIT-BIH errors, run 2 is in-sample. The held-out check below
decides whether the revision generalizes.

**Held-out: INCART (`ecg_incart_heldout.json`).** ECG_INCART_DETAIL

## Respiration — BIDMC PPG and Respiration Dataset — PASS

53 ICU recordings (125 Hz, 8 min each), impedance pneumography, breaths annotated by two independent annotators.
Rate uses 60 s windows with 50% overlap. Breath F1 uses a tolerance of 25% of the median breath interval.

| Metric | Value | Criterion |
|---|---|---|
| Breath detection F1 vs annotator 1 (peak convention) | 0.954 (TP 6829, FP 414, FN 241) | ≥ 0.90 (fail < 0.80) |
| Rate MAE vs annotator 1 (n = 794 windows) | 0.36 bpm | ≤ 1 bpm (fail > 3) |
| Inter-annotator rate MAE | 0.38 bpm | — |
| MAE minus inter-annotator | −0.02 bpm | ≤ 0.5 (fail > 2) |
| Irregular breathing (top quartile of breath-interval CV, n = 199) | 0.60 bpm | (reported) |
| Ti/Te | **BLOCKED** | no inspiratory/expiratory phase annotations |

The breath marker convention (peaks vs troughs) was chosen on this data (one degree of freedom). Rate does not depend
on it. Motion artifacts are rare in an ICU population, so motion handling is untested.

## EDA — Non-EEG Dataset — FAIL

20 healthy adults, wrist EDA at 8 Hz with stage markers (relax, physical, relax, mini-emotional, cognitive, relax,
emotional, relax), accelerometry.

| Metric | Value | Criterion | Verdict |
|---|---|---|---|
| Tonic correlation vs NeuroKit2 (median) | 1.00 | ≥ 0.90 (fail < 0.70) | PASS (uninformative: both split at 0.05 Hz) |
| SCR peak F1 vs NeuroKit2 (1 s window, mean over subjects) | 0.380 | ≥ 0.60 (fail < 0.40) | **FAIL** |
| Cognitive − relax SCR rate, one-sided Wilcoxon | +6.8 /min, p = 1e-4 | p ≤ 0.05 | PASS |

Additional stage contrasts (each vs the first relax period): emotional +0.84 SCR/min (p = 6e-4), physical
+3.5 SCR/min (p = 2e-4). Tonic level rises in all three (p ≤ 1e-4).

Diagnostics (post hoc, do not change the verdict):
- Restricting our SCRs to ≥ 10% of each recording's largest response (NeuroKit2's relative `amplitude_min`) raises
  F1 to 0.505. The disagreement is mostly about the response definition. No event-level ground truth exists to
  say which definition is right.
- Median onset offset vs NeuroKit2: −0.125 s (tangent method) vs −0.25 s (legacy threshold method).
- The EDA-only artifact detector flagged the same fraction in physical-stress (treadmill) and relax stages
  (median difference 0.0), while accelerometer SD rose by 0.086 g. **Motion artifacts are not detected from EDA
  alone.**
- The dataset's EDA unit is undocumented (header "NU"); absolute amplitude thresholds assume µS.

### EDA onset bias (synthetic benchmark, `eda_synthetic_bias.json`)

120 SCRs with known onsets, linear drift added. Onset bias = detected − true.

| Method | Drift 0 | 0.6 µS/min | 1.2 | 2.4 |
|---|---|---|---|---|
| Legacy threshold: median bias (s) | −0.28 | −0.34 | −0.34 | −0.36 |
| Legacy threshold: missed / spurious | 0 / 0 | 0 / 38 | 60 / 0 | 80 / 0 |
| Tangent + drift-corrected derivative: median bias (s) | −0.09 | −0.09 | −0.14 | −0.19 |
| Tangent: missed / spurious | 0 / 0 | 0 / 7 | 0 / 7 | 0 / 7 |

The tangent method (now the default) removes most of the ~0.3 s early-onset bias and the drift-induced false or
missed responses on synthetic data. Real-data onset accuracy cannot be checked without annotated onsets.

## fNIRS — MNE `fnirs_motor` (NIRx, 1 participant) — PASS

| Check | Value | Criterion |
|---|---|---|
| SNIRF write (MNE-NIRS) → our reader: geometry max error | 0.0 m | ≤ 1e-6 m (fail > 1 mm) |
| Wavelengths preserved | yes | — |
| HbO vs MNE OD + Beer-Lambert (ppf 6): min r over channels | 1.000 | ≥ 0.999 (fail < 0.99) |
| GLM t (tapping) vs MNE-NIRS `run_glm`: r over 28 channels | 0.953 | ≥ 0.80 (fail < 0.50) |
| Channels with t > 3 | 25 / 28 | — |
| HbO block-average peak latency (top-25% channels by t) | 7.3 s | within 3 s of 6 s (fail > 6) |
| HbR anticorrelated with HbO | yes | — |
| Scalp coupling index median (fraction ≥ 0.8) | 0.92 (0.71) | (reported) |

Refusals checked: missing wavelength, missing source/detector geometry, PPG labelled as fNIRS, missing partial
pathlength factor. Each raised an explicit error with no silent default.

Limits: one participant. OD and Beer-Lambert delegate to MNE, so r = 1.000 tests integration, not independent physics.
Short-channel regression ran, but its benefit was not evaluated.

## Not validated

- PPG: no PPG pipeline in scope.
- Respiration Ti/Te: BLOCKED (no phase reference).
- EDA, respiration and ECG under motion: not represented in these datasets.
- Wearable ECG: MIT-BIH and INCART are clinical Holter recordings.

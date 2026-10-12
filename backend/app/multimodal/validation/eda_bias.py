"""SCR onset-bias and drift false-positive benchmark (synthetic ground truth; old vs new detector)."""
from __future__ import annotations

import numpy as np

from app.multimodal.acquisition.synthetic_signals import synth_eda
from app.multimodal.processing.eda import decompose, detect_scrs

ONSETS = (10.0, 40.0, 70.0, 100.0, 130.0, 160.0)
AMPS = (0.3, 0.1, 0.5, 0.05, 0.2, 0.08)


def run(seeds: int = 20, drifts=(0.0, 0.2, 0.6, 1.2), fs: float = 32.0) -> dict:
    out = {}
    for method in ("threshold", "tangent"):
        for drift in drifts:
            bias, miss, spurious, amp_err = [], 0, 0, []
            for seed in range(seeds):
                x, truth = synth_eda(fs, 190, np.random.default_rng(seed), ONSETS, AMPS, drift_us_per_min=drift)
                dec = decompose(x, fs)
                scrs = detect_scrs(dec.cleaned, fs, dec.artifact_mask, method=method)
                used = set()
                for t_on, t_pk, a in zip(truth.values["scr_response_onsets_s"], truth.values["scr_peak_times_s"],
                                         truth.values["scr_amplitudes_us"]):
                    cand = [i for i, s in enumerate(scrs) if abs(s.peak_s - t_pk) < 0.75 and i not in used]
                    if not cand:
                        miss += 1
                        continue
                    i = cand[0]
                    used.add(i)
                    bias.append(scrs[i].onset_s - t_on)
                    amp_err.append((scrs[i].amplitude_us - a) / a)
                spurious += len(scrs) - len(used)
            out[f"{method}|drift={drift}"] = {
                "median_onset_bias_s": float(np.median(bias)) if bias else None,
                "iqr_onset_bias_s": [float(np.percentile(bias, 25)), float(np.percentile(bias, 75))] if bias else None,
                "median_rel_amplitude_error": float(np.median(amp_err)) if amp_err else None,
                "missed": miss, "spurious": spurious, "n_true": seeds * len(ONSETS),
            }
    return out

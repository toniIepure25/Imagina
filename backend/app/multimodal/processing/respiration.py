"""Respiration: cycle detection, rate, inspiratory/expiratory timing, regularity, optional RSA coupling."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

from app.multimodal.processing.common import Feature, FeatureSet, butter_filter, flatline_fraction, withheld
from app.multimodal.schemas import Modality, SourceKind

MIN_PERIOD_S, MAX_PERIOD_S = 1.5, 20.0


@dataclass
class BreathCycles:
    onsets_s: np.ndarray
    peaks_s: np.ndarray
    ti_s: np.ndarray
    te_s: np.ndarray
    periods_s: np.ndarray
    amplitudes: np.ndarray


def detect_cycles(x: np.ndarray, fs: float) -> BreathCycles:
    filt = butter_filter(np.asarray(x, dtype=float).ravel(), fs, 0.05, 1.0)
    spread = np.subtract(*np.percentile(filt, [90, 10]))
    prom = 0.3 * spread
    peaks, _ = sps.find_peaks(filt, distance=int(MIN_PERIOD_S * fs), prominence=prom)
    troughs, _ = sps.find_peaks(-filt, distance=int(MIN_PERIOD_S * fs), prominence=prom)
    onsets, pk, ti, te, amp = [], [], [], [], []
    for tr in troughs:
        nxt_p = peaks[peaks > tr]
        if not nxt_p.size:
            break
        p = nxt_p[0]
        nxt_t = troughs[troughs > p]
        if not nxt_t.size:
            break
        between = troughs[(troughs > tr) & (troughs < p)]
        if between.size:
            continue
        onsets.append(tr / fs)
        pk.append(p / fs)
        ti.append((p - tr) / fs)
        te.append((nxt_t[0] - p) / fs)
        amp.append(filt[p] - filt[tr])
    o = np.array(onsets)
    periods = np.array(ti) + np.array(te)
    ok = (periods >= MIN_PERIOD_S) & (periods <= MAX_PERIOD_S)
    return BreathCycles(o[ok], np.array(pk)[ok], np.array(ti)[ok], np.array(te)[ok], periods[ok], np.array(amp)[ok])


def respiration_features(x: np.ndarray, fs: float, stream_id: str = "resp",
                         source_kind: SourceKind = SourceKind.SYNTHETIC, t_start: float = 0.0) -> FeatureSet:
    x = np.asarray(x, dtype=float).ravel()
    dur = x.size / fs
    fsets = FeatureSet(modality=Modality.RESPIRATION, stream_id=stream_id, source_kind=source_kind,
                       t_start=t_start, t_end=t_start + dur, quality=0.0)
    if flatline_fraction(x, fs, win_s=5.0) > 0.3:
        fsets.flags.append("flatline")
    c = detect_cycles(x, fs)
    method = "bandpass0.05-1+peak_trough"
    n = c.periods_s.size
    if n < 2:
        fsets.add(Feature(name="n_cycles", value=float(n), unit="count", method=method))
        for name, unit in [("resp_rate", "breaths/min"), ("ti_te_ratio", "ratio"), ("period_cv", "ratio"),
                           ("breath_regularity", "ratio")]:
            fsets.add(withheld(name, unit, "fewer than 2 complete cycles", method))
        return fsets
    covered = float(c.periods_s.sum() / dur)
    cv = float(np.std(c.periods_s, ddof=1) / np.mean(c.periods_s))
    amp_cv = float(np.std(c.amplitudes) / (np.mean(c.amplitudes) + 1e-12))
    fsets.quality = float(np.clip(min(1.0, covered / 0.7) * (1 - min(amp_cv, 1.0) * 0.5), 0, 1))
    if "flatline" in fsets.flags:
        fsets.quality *= 0.2
    q = fsets.quality
    fsets.add(Feature(name="n_cycles", value=float(n), unit="count", method=method))
    fsets.add(Feature(name="resp_rate", value=60.0 / float(np.mean(c.periods_s)), unit="breaths/min", confidence=q,
                      method=method))
    fsets.add(Feature(name="ti_te_ratio", value=float(np.mean(c.ti_s / c.te_s)), unit="ratio", confidence=q,
                      method=method))
    fsets.add(Feature(name="period_cv", value=cv, unit="ratio", confidence=q, method=method))
    fsets.add(Feature(name="breath_regularity", value=float(np.clip(1.0 - cv, 0, 1)), unit="ratio", confidence=q,
                      method=method))
    return fsets


def rsa_peak_to_trough(r_peak_times_s: np.ndarray, cycles: BreathCycles, ecg_quality: float, resp_quality: float,
                       min_quality: float = 0.6, min_breaths: int = 5) -> Feature:
    method = "peak_to_trough_per_breath"
    if ecg_quality < min_quality or resp_quality < min_quality:
        return withheld("rsa_p2t", "ms", "ECG or respiration quality below threshold", method)
    if cycles.periods_s.size < min_breaths:
        return withheld("rsa_p2t", "ms", f"fewer than {min_breaths} breaths", method)
    rr = np.diff(r_peak_times_s) * 1000.0
    rt = r_peak_times_s[1:]
    vals = []
    for onset, period in zip(cycles.onsets_s, cycles.periods_s):
        m = (rt >= onset) & (rt < onset + period)
        if m.sum() >= 2:
            vals.append(rr[m].max() - rr[m].min())
    if len(vals) < min_breaths:
        return withheld("rsa_p2t", "ms", "too few breaths containing >= 2 beats", method)
    return Feature(name="rsa_p2t", value=float(np.mean(vals)), unit="ms", confidence=min(ecg_quality, resp_quality),
                   method=method)

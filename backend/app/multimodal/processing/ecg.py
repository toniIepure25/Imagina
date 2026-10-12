"""ECG R-peak detection and HRV.

R-peaks: Pan-Tompkins-style band-pass / derivative / squaring / moving-window integration with refinement on the
filtered ECG. Ectopic/artifact beats: physiological range plus a 20% deviation rule against the local median RR
(Malik-style). HRV is computed only from normal-to-normal (NN) intervals. LF/HF is withheld unless the window is
>= 120 s and >= 90% of intervals are normal (short windows make LF power unreliable).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import interpolate
from scipy import signal as sps

from app.multimodal.processing.common import Feature, FeatureSet, butter_filter, flatline_fraction, withheld
from app.multimodal.schemas import Modality, SourceKind

MIN_RR_S, MAX_RR_S = 0.3, 2.0
LFHF_MIN_WINDOW_S = 120.0


@dataclass
class RPeakResult:
    peaks: np.ndarray
    rr_s: np.ndarray
    normal: np.ndarray
    template_corr: float


REFRACTORY_S, T_WAVE_S, SEARCHBACK_RR = 0.2, 0.36, 1.66


def _adaptive_select(integ: np.ndarray, deriv: np.ndarray, cand: np.ndarray, fs: float) -> list[int]:
    learn = integ[: int(2 * fs)] if integ.size > 2 * fs else integ
    spk, npk = 0.25 * float(learn.max()), 0.5 * float(learn.mean())
    win = max(int(0.075 * fs), 1)
    slope = np.array([np.abs(deriv[max(0, c - win):c + 1]).max() for c in cand])
    beats: list[int] = []
    rrs: list[int] = []
    last_i = -1
    for i, c in enumerate(cand):
        v = integ[c]
        thr = npk + 0.25 * (spk - npk)
        if beats and len(rrs) >= 2:
            limit = SEARCHBACK_RR * np.mean(rrs[-8:])
            if c - beats[-1] > limit:
                between = [j for j in range(last_i + 1, i)
                           if cand[j] - beats[-1] > REFRACTORY_S * fs and integ[cand[j]] > 0.5 * thr]
                if between:
                    j = max(between, key=lambda k: integ[cand[k]])
                    rrs.append(int(cand[j] - beats[-1]))
                    beats.append(int(cand[j]))
                    last_i = j
                    spk = 0.25 * integ[cand[j]] + 0.75 * spk
                    thr = npk + 0.25 * (spk - npk)
        if v <= thr:
            npk = 0.125 * v + 0.875 * npk
            continue
        if beats and c - beats[-1] < T_WAVE_S * fs and slope[i] < 0.5 * slope[last_i]:
            npk = 0.125 * v + 0.875 * npk
            continue
        if beats:
            rrs.append(int(c - beats[-1]))
        beats.append(int(c))
        last_i = i
        spk = 0.125 * v + 0.875 * spk
    return beats


def detect_r_peaks(ecg: np.ndarray, fs: float) -> np.ndarray:
    filt = butter_filter(ecg, fs, 5.0, 15.0)
    if np.abs(np.percentile(filt, 0.5)) > np.abs(np.percentile(filt, 99.5)):
        filt = -filt
    deriv = np.gradient(filt)
    integ = np.convolve(deriv ** 2, np.ones(max(int(0.15 * fs), 1)) / max(int(0.15 * fs), 1), mode="same")
    cand, _ = sps.find_peaks(integ, distance=max(int(REFRACTORY_S * fs), 1))
    if cand.size == 0:
        return np.zeros(0, dtype=int)
    half = int(0.1 * fs)
    peaks = []
    for c in _adaptive_select(integ, deriv, cand, fs):
        lo, hi = max(0, c - half), min(len(filt), c + half)
        seg = filt[lo:hi]
        peaks.append(lo + int(np.argmax(np.abs(seg))))
    return np.unique(np.array(peaks, dtype=int))


def classify_beats(rr: np.ndarray, deviation: float = 0.2) -> np.ndarray:
    normal = (rr >= MIN_RR_S) & (rr <= MAX_RR_S)
    if rr.size >= 3:
        pad = np.pad(rr, 2, mode="edge")
        local_med = np.array([np.median(pad[i:i + 5]) for i in range(rr.size)])
        normal &= np.abs(rr - local_med) <= deviation * local_med
    bad = np.where(~normal)[0]
    for k in bad:
        if k + 1 < normal.size and rr[k] < np.median(rr):
            normal[k + 1] = False
    return normal


def _template_corr(ecg: np.ndarray, peaks: np.ndarray, fs: float) -> float:
    half = int(0.25 * fs)
    beats = [ecg[p - half:p + half] for p in peaks if p - half >= 0 and p + half <= len(ecg)]
    if len(beats) < 3:
        return 0.0
    beats_arr = np.array(beats)
    tmpl = beats_arr.mean(axis=0)
    cors = [np.corrcoef(b, tmpl)[0, 1] for b in beats_arr]
    return float(np.clip(np.nanmedian(cors), 0, 1))


def analyze_rpeaks(ecg: np.ndarray, fs: float) -> RPeakResult:
    peaks = detect_r_peaks(ecg, fs)
    rr = np.diff(peaks) / fs
    normal = classify_beats(rr) if rr.size else np.zeros(0, dtype=bool)
    return RPeakResult(peaks, rr, normal, _template_corr(butter_filter(ecg, fs, 0.5, 40.0), peaks, fs))


def nn_successive_diffs_ms(rr: np.ndarray, normal: np.ndarray) -> np.ndarray:
    both = normal[:-1] & normal[1:]
    return (np.diff(rr) * 1000.0)[both]


def lf_hf(rr: np.ndarray, normal: np.ndarray, beat_times: np.ndarray) -> tuple[float, float, float]:
    t, nn = beat_times[normal], rr[normal]
    fs_i = 4.0
    grid = np.arange(t[0], t[-1], 1.0 / fs_i)
    nn_i = interpolate.CubicSpline(t, nn * 1000.0)(grid)
    nn_i = sps.detrend(nn_i)
    f, p = sps.welch(nn_i, fs=fs_i, nperseg=min(256, len(nn_i)), detrend="constant")
    lf_band = (f >= 0.04) & (f < 0.15)
    hf_band = (f >= 0.15) & (f < 0.40)
    lf = float(np.trapezoid(p[lf_band], f[lf_band]))
    hf = float(np.trapezoid(p[hf_band], f[hf_band]))
    return lf, hf, lf / hf if hf > 0 else float("nan")


def ecg_features(ecg: np.ndarray, fs: float, stream_id: str = "ecg", source_kind: SourceKind = SourceKind.SYNTHETIC,
                 t_start: float = 0.0) -> FeatureSet:
    x = np.asarray(ecg, dtype=float).ravel()
    dur = x.size / fs
    fsets = FeatureSet(modality=Modality.ECG, stream_id=stream_id, source_kind=source_kind, t_start=t_start,
                       t_end=t_start + dur, quality=0.0)
    if flatline_fraction(x, fs) > 0.2:
        fsets.flags.append("flatline")
    r = analyze_rpeaks(x, fs)
    n_int = r.rr_s.size
    frac_normal = float(r.normal.mean()) if n_int else 0.0
    expected_beats = dur / 1.0
    plausible = 0.3 * expected_beats <= len(r.peaks) <= 3.5 * expected_beats
    quality = frac_normal * r.template_corr * (1.0 if plausible else 0.3)
    if "flatline" in fsets.flags:
        quality *= 0.2
    fsets.quality = float(np.clip(quality, 0, 1))
    if n_int and frac_normal < 0.8:
        fsets.flags.append("many_ectopic_or_artifact_beats")
    method = "pan_tompkins_like+malik20"
    fsets.add(Feature(name="n_beats", value=float(len(r.peaks)), unit="count", method=method))
    fsets.add(Feature(name="fraction_normal_beats", value=frac_normal, unit="ratio", method=method))
    nn = r.rr_s[r.normal]
    if nn.size < 2:
        for name, unit in [("heart_rate", "bpm"), ("rmssd", "ms"), ("sdnn", "ms"), ("pnn50", "%")]:
            fsets.add(withheld(name, unit, "fewer than 2 normal intervals", method))
    else:
        conf = fsets.quality
        fsets.add(Feature(name="heart_rate", value=60.0 / float(np.mean(nn)), unit="bpm", confidence=conf,
                          method=method))
        sd = nn_successive_diffs_ms(r.rr_s, r.normal)
        if sd.size >= 2:
            fsets.add(Feature(name="rmssd", value=float(np.sqrt(np.mean(sd ** 2))), unit="ms", confidence=conf,
                              method=method + ";nn_pairs_only"))
            fsets.add(Feature(name="pnn50", value=float(np.mean(np.abs(sd) > 50.0) * 100.0), unit="%",
                              confidence=conf, method=method))
        else:
            fsets.add(withheld("rmssd", "ms", "insufficient adjacent normal pairs", method))
            fsets.add(withheld("pnn50", "%", "insufficient adjacent normal pairs", method))
        sdnn_reason = "" if dur >= 60 else f"ultra-short window ({dur:.0f}s); SDNN not comparable to 5-min norms"
        fsets.add(Feature(name="sdnn", value=float(np.std(nn * 1000.0, ddof=1)), unit="ms",
                          confidence=conf * (1.0 if dur >= 60 else 0.5), method=method, reason=sdnn_reason))
    if dur < LFHF_MIN_WINDOW_S:
        reason = f"window {dur:.0f}s < {LFHF_MIN_WINDOW_S:.0f}s required for LF estimation"
    elif frac_normal < 0.9:
        reason = f"only {frac_normal:.0%} normal intervals (< 90%)"
    else:
        reason = ""
    if reason:
        for name, unit in [("lf_power", "ms2"), ("hf_power", "ms2"), ("lf_hf_ratio", "ratio")]:
            fsets.add(withheld(name, unit, reason, "welch_4hz_cubic"))
    else:
        beat_t = r.peaks[1:] / fs
        lf, hf, ratio = lf_hf(r.rr_s, r.normal, beat_t)
        for name, val, unit in [("lf_power", lf, "ms2"), ("hf_power", hf, "ms2"), ("lf_hf_ratio", ratio, "ratio")]:
            fsets.add(Feature(name=name, value=val, unit=unit, confidence=fsets.quality * 0.8,
                              method="welch_4hz_cubic",
                              reason="LF/HF is not a validated sympathovagal balance index; interpret cautiously"
                              if name == "lf_hf_ratio" else ""))
    return fsets

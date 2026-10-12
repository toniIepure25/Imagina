"""EDA: tonic/phasic decomposition, SCR detection, artifact handling, event-related responses, baseline calibration.

Tonic = 0.05 Hz low-pass of the cleaned signal; phasic = residual. SCRs are detected on the smoothed signal: a peak is a
derivative zero-crossing; its onset is the last sample before the steepest rise (within 5 s) whose slope is
below max(0.01 uS/s, 10% of the peak slope). Responses
need amplitude >= 0.01 uS (common minimum-amplitude criterion) and a 0.3-5 s rise time.

``method="tangent"`` (default) refines the onset to where the tangent at the steepest rise meets the pre-response
level (reduces the early bias caused by zero-phase smoothing) and measures amplitude against the 2 s pre-onset trend
extrapolated to the peak, so slow tonic drift is not counted as a response. Peaks and onsets are found on the
derivative minus its 20 s running median, so responses riding on a steadily rising baseline are not missed.
``method="threshold"`` is the earlier behaviour, kept for comparison.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.multimodal.processing.common import Feature, FeatureSet, butter_filter, flatline_fraction, withheld
from app.multimodal.schemas import EvidenceClass, Marker, Modality, SourceKind

MIN_SCR_AMPLITUDE_US = 0.01
PHYSIOLOGICAL_RANGE_US = (0.05, 60.0)
MAX_SLOPE_US_PER_S = 10.0
ONSET_SLOPE_US_PER_S = 0.01
ONSET_FRACTION_OF_PEAK_SLOPE = 0.1
MIN_RISE_S, MAX_RISE_S = 0.3, 5.0
PRE_TREND_S = 2.0
DRIFT_WINDOW_S = 20.0


@dataclass
class SCR:
    onset_s: float
    peak_s: float
    amplitude_us: float
    rise_time_s: float


@dataclass
class EDADecomposition:
    cleaned: np.ndarray
    tonic: np.ndarray
    phasic: np.ndarray
    artifact_mask: np.ndarray
    scrs: list[SCR]


def artifact_mask(x: np.ndarray, fs: float) -> np.ndarray:
    lo, hi = PHYSIOLOGICAL_RANGE_US
    bad = (x < lo) | (x > hi)
    slope = np.abs(np.gradient(x) * fs)
    bad |= slope > MAX_SLOPE_US_PER_S
    pad = int(1.0 * fs)
    if bad.any():
        bad = np.convolve(bad.astype(float), np.ones(2 * pad + 1), mode="same") > 0
    return bad


def decompose(x: np.ndarray, fs: float) -> EDADecomposition:
    x = np.asarray(x, dtype=float).ravel()
    mask = artifact_mask(x, fs)
    filled = x.copy()
    if mask.any() and (~mask).sum() > 2:
        idx = np.arange(x.size)
        filled[mask] = np.interp(idx[mask], idx[~mask], x[~mask])
    cleaned = butter_filter(filled, fs, None, min(1.0, fs / 2.5)) if fs > 2.5 else filled
    tonic = butter_filter(cleaned, fs, None, 0.05)
    phasic = cleaned - tonic
    return EDADecomposition(cleaned, tonic, phasic, mask, detect_scrs(cleaned, fs, mask))


def detect_scrs(cleaned: np.ndarray, fs: float, mask: np.ndarray | None = None,
                method: str = "tangent") -> list[SCR]:
    smooth = butter_filter(cleaned, fs, None, min(0.5, fs / 2.5)) if fs > 2.5 else cleaned
    d = np.gradient(smooth) * fs
    d_fine = np.gradient(cleaned) * fs
    if method == "tangent":
        from scipy.ndimage import median_filter

        drift = median_filter(d, size=max(3, int(DRIFT_WINDOW_S * fs)) | 1, mode="nearest")
        d = d - drift
        d_fine = d_fine - drift
    peaks = np.where((d[:-1] > 0) & (d[1:] <= 0))[0] + 1
    max_rise = int(MAX_RISE_S * fs)
    out = []
    last_peak = -1
    for p in peaks:
        lo = max(last_peak + 1, p - max_rise)
        if p - lo < 2:
            continue
        steepest = lo + int(np.argmax(d[lo:p]))
        thr = max(ONSET_SLOPE_US_PER_S, ONSET_FRACTION_OF_PEAK_SLOPE * d[steepest])
        below = np.where(d[lo:steepest] < thr)[0]
        if not below.size:
            continue
        o = lo + int(below[-1])
        fine_steep = o + int(np.argmax(d_fine[o:steepest + 1]))
        fine_below = np.where(d_fine[o:fine_steep] < max(ONSET_SLOPE_US_PER_S,
                                                           ONSET_FRACTION_OF_PEAK_SLOPE * d_fine[fine_steep]))[0]
        if fine_below.size:
            o = o + int(fine_below[-1])
        amp = float(smooth[p] - smooth[o])
        if method == "tangent":
            fs_i = o + int(np.argmax(d_fine[o:p + 1]))
            if d_fine[fs_i] > 0:
                o_t = fs_i - (cleaned[fs_i] - cleaned[o]) / d_fine[fs_i] * fs
                o = int(np.clip(round(o_t), o, fs_i))
            pre = max(0, o - int(PRE_TREND_S * fs))
            if o - pre >= 3:
                slope, icpt = np.polyfit(np.arange(pre, o), smooth[pre:o], 1)
                amp = min(amp, float(smooth[p] - (icpt + slope * p)))
        rise = (p - o) / fs
        if amp < MIN_SCR_AMPLITUDE_US or not MIN_RISE_S <= rise <= MAX_RISE_S:
            continue
        if mask is not None and mask[o:p + 1].any():
            continue
        out.append(SCR(o / fs, p / fs, amp, rise))
        last_peak = p
    return out


@dataclass
class EDABaseline:
    tonic_mean_us: float
    tonic_sd_us: float
    scr_rate_per_min: float
    n_samples: int


def calibrate_baseline(x: np.ndarray, fs: float) -> EDABaseline:
    dec = decompose(x, fs)
    good = ~dec.artifact_mask
    dur_min = x.size / fs / 60.0
    return EDABaseline(float(np.mean(dec.tonic[good])), float(np.std(dec.tonic[good]) + 1e-6),
                       len(dec.scrs) / dur_min if dur_min > 0 else 0.0, int(good.sum()))


def event_related_scr(dec: EDADecomposition, markers: list[Marker], t0: float,
                      window: tuple[float, float] = (1.0, 4.0)) -> list[dict]:
    out = []
    for mk in markers:
        rel = mk.local_time - t0
        hits = [s for s in dec.scrs if window[0] <= s.onset_s - rel <= window[1]]
        best = max(hits, key=lambda s: s.amplitude_us) if hits else None
        out.append({
            "marker": mk.label, "marker_time": mk.local_time,
            "responded": best is not None,
            "amplitude_us": best.amplitude_us if best else 0.0,
            "latency_s": (best.onset_s - rel) if best else None,
        })
    return out


def eda_features(x: np.ndarray, fs: float, stream_id: str = "eda", source_kind: SourceKind = SourceKind.SYNTHETIC,
                 t_start: float = 0.0, baseline: EDABaseline | None = None,
                 markers: list[Marker] | None = None) -> tuple[FeatureSet, EDADecomposition]:
    x = np.asarray(x, dtype=float).ravel()
    dur = x.size / fs
    fsets = FeatureSet(modality=Modality.EDA, stream_id=stream_id, source_kind=source_kind, t_start=t_start,
                       t_end=t_start + dur, quality=0.0)
    dec = decompose(x, fs)
    art = float(dec.artifact_mask.mean())
    flat = flatline_fraction(x, fs, win_s=5.0, tol=1e-4)
    if art > 0:
        fsets.flags.append("artifact_segments")
    if flat > 0.3:
        fsets.flags.append("flatline_possible_contact_loss")
    fsets.quality = float(np.clip((1 - art) * (1 - flat), 0, 1))
    method = "lowpass0.05_tonic+deriv_scr"
    good = ~dec.artifact_mask
    if good.sum() < fs * 2:
        for name, unit in [("tonic_scl", "uS"), ("scr_rate", "1/min"), ("scr_mean_amplitude", "uS")]:
            fsets.add(withheld(name, unit, "insufficient artifact-free data", method))
        return fsets, dec
    fsets.add(Feature(name="tonic_scl", value=float(np.mean(dec.tonic[good])), unit="uS",
                      confidence=fsets.quality, method=method))
    fsets.add(Feature(name="scr_rate", value=len(dec.scrs) / (dur / 60.0), unit="1/min",
                      confidence=fsets.quality, method=method))
    amps = [s.amplitude_us for s in dec.scrs]
    fsets.add(Feature(name="scr_mean_amplitude", value=float(np.mean(amps)) if amps else 0.0, unit="uS",
                      confidence=fsets.quality, method=method))
    fsets.add(Feature(name="phasic_auc", value=float(np.trapezoid(np.clip(dec.phasic, 0, None)) / fs), unit="uS*s",
                      confidence=fsets.quality, method=method))
    if baseline is not None:
        z = (float(np.mean(dec.tonic[good])) - baseline.tonic_mean_us) / baseline.tonic_sd_us
        fsets.add(Feature(name="tonic_scl_z_vs_baseline", value=z, unit="z", confidence=fsets.quality,
                          method="individual_baseline", evidence_class=EvidenceClass.DERIVED_METRIC))
    if markers:
        er = event_related_scr(dec, markers, t_start)
        fsets.add(Feature(name="event_response_rate", value=float(np.mean([e["responded"] for e in er])),
                          unit="ratio", confidence=fsets.quality, method="scr_onset_1-4s_post_event"))
    return fsets, dec

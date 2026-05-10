"""Experimental EEG DSP pipeline.

Bandpower extraction chain:
  1. scipy.signal.welch (if available)
  2. numpy FFT (if available, scipy unavailable)
  3. existing heuristic fallback

All outputs are experimental proxy estimates, not clinical EEG biomarkers.
"""

import math

BANDS = {
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}

DSP_VERSION = "v2.4_welch"


def _has_scipy():
    try:
        import scipy.signal  # noqa: F401
        return True
    except ImportError:
        return False


def _has_numpy():
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def compute_bandpowers(samples: list[list[float]], sfreq: float, bands: dict | None = None) -> dict:
    bands = bands or BANDS
    if _has_scipy():
        return _welch_bandpowers(samples, sfreq, bands)
    if _has_numpy():
        return _numpy_fft_bandpowers(samples, sfreq, bands)
    return _heuristic_bandpowers(samples, sfreq, bands)


def _welch_bandpowers(samples, sfreq, bands):
    import numpy as np
    from scipy.signal import welch as scipy_welch

    arr = np.array(samples, dtype=np.float64)
    if arr.ndim == 2:
        arr = arr.mean(axis=1)
    nperseg = min(256, len(arr))
    if nperseg < 32:
        return {k: 0.4 for k in bands}

    freqs, psd = scipy_welch(arr, fs=sfreq, nperseg=nperseg, detrend="linear")
    psd_total = float(np.trapezoid(psd, freqs))
    if psd_total <= 0:
        return {k: 0.4 for k in bands}

    result = {}
    for band_name, (lo, hi) in bands.items():
        if hi > sfreq / 2:
            result[band_name] = 0.0
            continue
        mask = (freqs >= lo) & (freqs <= hi)
        if not mask.any():
            result[band_name] = 0.0
            continue
        band_power = np.trapezoid(psd[mask], freqs[mask])
        result[band_name] = float(band_power / psd_total)

    total = sum(result.values()) or 1.0
    return {k: v / total for k, v in result.items()}


def _numpy_fft_bandpowers(samples, sfreq, bands):
    bands = bands or BANDS
    import numpy as np

    arr = np.array(samples, dtype=np.float64)
    if arr.ndim == 2:
        arr = arr.mean(axis=1)
    n = len(arr)
    if n < 4:
        return {k: 0.4 for k in bands}

    fft_vals = np.abs(np.fft.rfft(arr))
    freqs = np.fft.rfftfreq(n, d=1.0 / max(sfreq, 1))
    fft_total = np.sum(fft_vals)
    if fft_total <= 0:
        return {k: 0.4 for k in bands}

    result = {}
    for band_name, (lo, hi) in bands.items():
        if hi > sfreq / 2:
            result[band_name] = 0.0
            continue
        mask = (freqs >= lo) & (freqs <= hi)
        if not mask.any():
            result[band_name] = 0.0
            continue
        result[band_name] = float(np.sum(fft_vals[mask]) / fft_total)

    total = sum(result.values()) or 1.0
    return {k: v / total for k, v in result.items()}


def _heuristic_bandpowers(samples, sfreq, bands):
    bands = bands or BANDS
    if not samples:
        return {k: 0.4 for k in bands}
    flat = []
    for ch in samples:
        flat.extend(ch)
    if not flat:
        return {k: 0.4 for k in bands}
    zcr = _zero_crossing_rate(flat)
    norm_zcr = min(1.0, max(0.0, zcr * sfreq / 60.0))
    return {
        "theta": max(0.0, 1.0 - norm_zcr * 1.5),
        "alpha": max(0.0, 1.0 - abs(norm_zcr - 0.5) * 2.0),
        "beta": min(1.0, norm_zcr * 1.5),
    }


def _zero_crossing_rate(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    c = [v - m for v in values]
    crosses = sum(1 for i in range(len(c) - 1) if c[i] * c[i + 1] <= 0)
    return crosses / len(c)


def compute_artifact_scores(samples):
    if not samples:
        return _default_artifact_scores()

    flat = []
    for ch in samples:
        flat.extend(list(ch))
    if not flat:
        return _default_artifact_scores()
    n = len(flat)
    missing = sum(1 for v in flat if not math.isfinite(v))
    valid = [v for v in flat if math.isfinite(v)]
    if not valid:
        return _default_artifact_scores()

    mdr = missing / n if n > 0 else 0.0
    mu = sum(valid) / len(valid)
    sd = math.sqrt(sum((v - mu) ** 2 for v in valid) / len(valid)) if len(valid) > 1 else 0.001

    peak = max(abs(v - mu) for v in valid)
    clipping = sum(1 for v in valid if abs(v - mu) > 4 * sd) / len(valid) if sd > 0 else 0.0
    drift = abs(mu) / max(sd, 0.001) * 0.2
    muscle = 0.0
    if len(valid) >= 4:
        diffs = [valid[i + 1] - valid[i] for i in range(len(valid) - 1)]
        muscle = math.sqrt(sum(d * d for d in diffs) / len(diffs)) / max(sd, 0.001) * 0.3

    return {
        "missing_data_ratio": min(1.0, max(0.0, mdr)),
        "clipping_score": min(1.0, max(0.0, clipping)),
        "drift_score": min(1.0, max(0.0, drift)),
        "muscle_score": min(1.0, max(0.0, muscle)),
        "blink_score": min(1.0, max(0.0, peak / max(1.0, 4 * sd) * 0.5)),
    }


def _default_artifact_scores():
    return {
        "missing_data_ratio": 1.0,
        "clipping_score": 0.0,
        "drift_score": 0.0,
        "muscle_score": 0.0,
        "blink_score": 0.0,
    }


def compute_signal_quality(artifact_scores, bandpowers):
    art_penalty = sum(
        artifact_scores.get(k, 0) * w
        for k, w in [("missing_data_ratio", 0.4), ("muscle_score", 0.3), ("clipping_score", 0.3)]
    )
    alpha_ratio = bandpowers.get("alpha", 0.4)
    return min(1.0, max(0.0, 1.0 - art_penalty * 0.8 + alpha_ratio * 0.2))


def extract_eeg_features(window, self_report=None):
    samples = window.samples
    sfreq = float(window.sampling_rate_hz or 256)

    if samples is None or len(samples) == 0:
        bp = {"theta": 0.4, "alpha": 0.45, "beta": 0.3}
        art = _default_artifact_scores()
        sq = 0.0
        real_signal = not ((window.generator_version or "").startswith("fixture"))
        return _build_result(window, bp, art, sq, real_signal, "dsp_fallback_no_samples")

    bp = compute_bandpowers(samples, sfreq)
    art = compute_artifact_scores(samples)
    sq = compute_signal_quality(art, bp)
    is_fixture = (window.generator_version or "").startswith("fixture")
    real_signal = not is_fixture and not window.simulated
    used = "welch" if _has_scipy() else ("fft" if _has_numpy() else "heuristic")

    return _build_result(window, bp, art, sq, real_signal, used)


def _build_result(window, bp, art, sq, real_signal, dsp_method):
    sr = window.sampling_rate_hz or 256
    return {
        "theta_power": round(min(1.0, max(0.0, bp.get("theta", 0.4))), 4),
        "alpha_power": round(min(1.0, max(0.0, bp.get("alpha", 0.45))), 4),
        "beta_power": round(min(1.0, max(0.0, bp.get("beta", 0.3))), 4),
        "theta_beta_ratio": round(max(0.0, bp.get("theta", 0.4) / max(bp.get("beta", 0.01), 0.01)), 4),
        "alpha_stability": round(min(1.0, max(0.0, bp.get("alpha", 0.5))), 4),
        "signal_quality": round(sq, 4),
        "simulated_imagery_strength": round(
            min(1.0, bp.get("alpha", 0.5) * 0.6 + (1 - art["missing_data_ratio"]) * 0.4), 4
        ),
        "behavioral_stability": round(min(1.0, 0.5 + sq * 0.4), 4),
        "reaction_time_ms": None,
        "real_signal": real_signal,
        "blink_score": round(art["blink_score"], 4),
        "muscle_score": round(art["muscle_score"], 4),
        "drift_score": round(art["drift_score"], 4),
        "clipping_score": round(art["clipping_score"], 4),
        "missing_data_ratio": round(art["missing_data_ratio"], 4),
        "preprocessing_version": f"{DSP_VERSION}_{dsp_method}",
        "feature_version": "v2.4",
        "channel_count": window.channel_count,
        "sampling_rate_hz": int(sr) if sr else None,
        "channels_used": window.channel_names,
        "provider_id": window.provider_id,
        "provider_type": window.provider_type,
        "artifact_flags": window.artifact_flags,
        "dsp_method": dsp_method,
    }

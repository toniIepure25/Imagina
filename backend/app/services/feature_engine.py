"""Normalizes and combines simulated features with self-report data.

For real EEG, provides simplified experimental bandpower and artifact proxies.
These are NOT clinical-grade EEG analysis.
"""

import math

from app.schemas.features import FeatureVector
from app.schemas.signals import EEGSampleWindow


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float], mean_val: float | None = None) -> float:
    if len(values) < 2:
        return 0.0
    m = mean_val if mean_val is not None else _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _zero_crossing_rate(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_val = _mean(values)
    centered = [v - mean_val for v in values]
    crosses = sum(1 for i in range(len(centered) - 1) if centered[i] * centered[i + 1] <= 0)
    return crosses / len(centered)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class FeatureEngine:
    def process(self, raw: FeatureVector, self_report: dict | None = None) -> FeatureVector:
        return raw

    def process_eeg_window(self, window: EEGSampleWindow, self_report: dict | None = None) -> FeatureVector:
        try:
            from app.services.eeg_dsp import extract_eeg_features
            feats = extract_eeg_features(window, self_report)
        except Exception:
            feats = _heuristic_fallback(window)

        sr = self_report or {}
        sr_focus = sr.get("focus", 5) / 10.0
        behavioral = min(1.0, max(0.0,
            0.5 + 0.25 * sr.get("stability", 5) / 10.0 + 0.15 * sr_focus
            - 0.20 * sr.get("distraction", 3) / 10.0 + feats.get("signal_quality", 0.5) * 0.1,
        ))
        imagery = min(1.0, max(0.0,
            feats.get("alpha_power", 0.5) * 0.5 + sr.get("vividness", 5) / 10.0 * 0.4
            + (1 - feats.get("missing_data_ratio", 0)) * 0.1,
        ))

        return FeatureVector(
            session_id=window.session_id,
            timestamp=window.timestamp,
            window_index=window.window_index,
            theta_power=feats.get("theta_power", 0.4),
            alpha_power=feats.get("alpha_power", 0.45),
            beta_power=feats.get("beta_power", 0.3),
            theta_beta_ratio=feats.get("theta_beta_ratio", 1.0),
            alpha_stability=feats.get("alpha_stability", 0.5),
            signal_quality=feats.get("signal_quality", 0.5),
            simulated_imagery_strength=imagery,
            behavioral_stability=behavioral,
            reaction_time_ms=feats.get("reaction_time_ms"),
            real_signal=feats.get("real_signal", False),
            provider_id=feats.get("provider_id"),
            provider_type=feats.get("provider_type"),
            channel_count=feats.get("channel_count"),
            sampling_rate_hz=feats.get("sampling_rate_hz"),
            channels_used=feats.get("channels_used"),
            artifact_flags=feats.get("artifact_flags"),
            blink_score=feats.get("blink_score"),
            muscle_score=feats.get("muscle_score"),
            drift_score=feats.get("drift_score"),
            clipping_score=feats.get("clipping_score"),
            missing_data_ratio=feats.get("missing_data_ratio"),
            preprocessing_version=feats.get("preprocessing_version"),
            feature_version=feats.get("feature_version", "v2.4"),
        )


def _heuristic_fallback(window):
    samples = window.samples
    if not samples:
        return {
            "theta_power": 0.4, "alpha_power": 0.45, "beta_power": 0.3,
            "theta_beta_ratio": 1.0, "alpha_stability": 0.5, "signal_quality": 0.0,
            "blink_score": 0.0, "muscle_score": 0.0, "drift_score": 0.0,
            "clipping_score": 0.0, "missing_data_ratio": 1.0,
            "real_signal": False, "preprocessing_version": "heuristic_fallback",
            "feature_version": "v2.4", "dsp_method": "heuristic",
        }
    flat = []
    for ch in samples:
        flat.extend(list(ch))
    valid = [v for v in flat if math.isfinite(v)]
    if not valid:
        return {
            "theta_power": 0.4, "alpha_power": 0.45, "beta_power": 0.3,
            "theta_beta_ratio": 1.0, "alpha_stability": 0.5, "signal_quality": 0.0,
            "blink_score": 0.0, "muscle_score": 0.0, "drift_score": 0.0,
            "clipping_score": 0.0, "missing_data_ratio": 1.0,
            "real_signal": False, "preprocessing_version": "heuristic_fallback",
            "feature_version": "v2.4", "dsp_method": "heuristic",
        }
    zcr = _zero_crossing_rate(valid)
    srate = max(1, window.sampling_rate_hz)
    norm_zcr = _clamp(zcr * srate / 60.0)
    mu = _mean(valid)
    sd = _std(valid, mu)
    return {
        "theta_power": _clamp(1.0 - norm_zcr * 1.5),
        "alpha_power": _clamp(1.0 - abs(norm_zcr - 0.5) * 2.0),
        "beta_power": _clamp(norm_zcr * 1.5),
        "theta_beta_ratio": _clamp(1.0 - norm_zcr * 1.5) / max(_clamp(norm_zcr * 1.5), 0.01),
        "alpha_stability": _clamp(1.0 - abs(norm_zcr - 0.5) * 2.0),
        "signal_quality": _clamp(0.3 + math.log(max(0.01, max(abs(v - mu) for v in valid) + 1)) * 0.3),
        "blink_score": _clamp(max(abs(v - mu) for v in valid) / max(1.0, 4 * max(sd, 0.001)) * 0.5),
        "muscle_score": 0.0,
        "drift_score": _clamp(abs(mu) / max(sd, 0.001) * 0.2),
        "clipping_score": 0.0,
        "missing_data_ratio": 0.0,
        "real_signal": not (window.generator_version or "").startswith("fixture"),
        "preprocessing_version": "heuristic_fallback",
        "feature_version": "v2.4",
        "dsp_method": "heuristic",
    }

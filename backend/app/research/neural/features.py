"""Prespecified classical EEG features and reliability analysis for C1.

Classical, interpretable features are computed and validated for reliability
before any deep-learning encoder is introduced (Commit 5), per the commit
plan. Every feature uses a frozen anatomical channel group and a frozen
frequency band — none of these are fit from data, so they carry no fold-
leakage risk and can be computed once per epoch, independent of any later
train/test split.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.signal import welch
from scipy.stats import entropy as _scipy_entropy

from app.research.neural.preprocessing import FRONTAL_PROXY_CHANNELS, POSTERIOR_CHANNELS

# Frozen anatomical channel groups (indices resolved against
# EXPECTED_YOTO_CHANNELS at call time, never fit from data).
CENTRAL_CHANNELS = ("FC3", "FCZ", "FC4", "C3", "CZ", "C4", "CP3", "CPZ", "CP4")

FROZEN_CHANNEL_GROUPS: dict[str, tuple[str, ...]] = {
    "frontal": FRONTAL_PROXY_CHANNELS,
    "central": CENTRAL_CHANNELS,
    "posterior": POSTERIOR_CHANNELS,
}

# Frozen frequency bands (Hz), standard EEG convention.
FROZEN_BANDS: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
}

FEATURES_VERSION = "1.0.0"


def _channel_indices(channel_names: list[str], group: tuple[str, ...]) -> list[int]:
    have = {c.upper(): i for i, c in enumerate(channel_names)}
    return [have[c] for c in group if c in have]


def _band_power(epoch: np.ndarray, sfreq: float, band: tuple[float, float]) -> float:
    """Mean Welch PSD power within [band[0], band[1]) Hz, averaged over the
    given channels' rows of `epoch` (already selected by the caller)."""
    low, high = band
    nperseg = min(epoch.shape[-1], int(sfreq * 2))
    if nperseg < 4:
        return 0.0
    freqs, psd = welch(epoch, fs=sfreq, nperseg=nperseg, axis=-1)
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return 0.0
    return float(psd[..., mask].mean())


def _spectral_entropy(epoch: np.ndarray, sfreq: float) -> float:
    nperseg = min(epoch.shape[-1], int(sfreq * 2))
    if nperseg < 4:
        return 0.0
    _freqs, psd = welch(epoch, fs=sfreq, nperseg=nperseg, axis=-1)
    psd_mean = psd.mean(axis=0) if psd.ndim > 1 else psd
    psd_norm = psd_mean / (psd_mean.sum() + 1e-20)
    return float(_scipy_entropy(psd_norm + 1e-20))


def _erp_amplitude_latency(epoch: np.ndarray, sfreq: float) -> tuple[float, float]:
    """Peak absolute amplitude and its latency (s), averaged across the
    given channels — a simple, interpretable ERP summary, not a component-
    specific (e.g. P300) detector."""
    trace = epoch.mean(axis=0) if epoch.ndim > 1 else epoch
    idx = int(np.argmax(np.abs(trace)))
    amplitude = float(trace[idx])
    latency = float(idx / sfreq)
    return amplitude, latency


@dataclass
class ClassicalFeatureVector:
    trial_id: str
    condition: str
    stimulus_id: str
    features: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id, "condition": self.condition,
            "stimulus_id": self.stimulus_id, "features": self.features,
        }


def extract_classical_features(
    epoch: np.ndarray, sfreq: float, channel_names: list[str],
    trial_id: str = "", condition: str = "", stimulus_id: str = "",
) -> ClassicalFeatureVector:
    """One epoch (n_channels, n_samples) -> a flat, named feature dict.

    Every feature name encodes exactly which frozen channel group and/or
    frozen band it came from, so features can be audited without re-reading
    this function.
    """
    features: dict[str, float] = {}

    for group_name, group_channels in FROZEN_CHANNEL_GROUPS.items():
        idx = _channel_indices(channel_names, group_channels)
        if not idx:
            continue
        region = epoch[idx, :]

        for band_name, band_range in FROZEN_BANDS.items():
            features[f"band_power__{group_name}__{band_name}"] = _band_power(region, sfreq, band_range)

        features[f"spectral_entropy__{group_name}"] = _spectral_entropy(region, sfreq)

        amp, lat = _erp_amplitude_latency(region, sfreq)
        features[f"erp_amplitude__{group_name}"] = amp
        features[f"erp_latency__{group_name}"] = lat

    # Alpha suppression/enhancement: posterior alpha power relative to
    # frontal alpha power — a standard proxy for visual engagement.
    posterior_alpha = features.get("band_power__posterior__alpha", 0.0)
    frontal_alpha = features.get("band_power__frontal__alpha", 0.0)
    if frontal_alpha > 0:
        features["alpha_posterior_frontal_ratio"] = posterior_alpha / frontal_alpha

    # Posterior vs frontal beta summary.
    posterior_beta = features.get("band_power__posterior__beta", 0.0)
    frontal_beta = features.get("band_power__frontal__beta", 0.0)
    if frontal_beta > 0:
        features["beta_posterior_frontal_ratio"] = posterior_beta / frontal_beta

    return ClassicalFeatureVector(trial_id=trial_id, condition=condition, stimulus_id=stimulus_id, features=features)


def split_half_reliability(vectors: list[ClassicalFeatureVector], feature_name: str, seed: int = 42) -> float | None:
    """Pearson correlation between two random, equal-sized halves' mean
    feature values — a coarse split-half reliability check. Returns None if
    there are too few trials to split meaningfully."""
    values = [v.features.get(feature_name) for v in vectors if feature_name in v.features]
    values = [v for v in values if v is not None]
    if len(values) < 6:
        return None
    rng = np.random.RandomState(seed)
    idx = rng.permutation(len(values))
    half = len(idx) // 2
    a = np.array(values)[idx[:half]]
    b = np.array(values)[idx[half:half * 2]]
    if a.std() == 0 or b.std() == 0:
        return None
    # Split-half correlation of two DIFFERENT trial subsets isn't directly
    # comparable pointwise; report the correlation of their sorted order as
    # a distribution-level consistency check (rank stability), not a
    # trial-paired reliability (that requires session_reliability below).
    return float(np.corrcoef(np.sort(a), np.sort(b))[0, 1])


def session_reliability(
    vectors_session_a: list[ClassicalFeatureVector], vectors_session_b: list[ClassicalFeatureVector],
    feature_name: str, min_shared_groups: int = 6,
) -> float | None:
    """Pearson correlation of a feature's per-(condition, stimulus_id) mean
    between two sessions of the SAME participant — the primary session-to-
    session reliability check enabled by ds005815's 2-session design.

    Deliberately grouped by (condition, stimulus_id) rather than by
    `condition` alone: `condition` only takes two values (perception,
    imagery), and a Pearson correlation over exactly two points is *always*
    +-1 regardless of the data — a spurious "perfect reliability" that
    reflects the degrees of freedom, not the feature. Grouping by
    (condition, stimulus_id) gives up to 2 x 27 = 54 possible groups, and
    `min_shared_groups` additionally guards against a similarly trivial
    small-n correlation when few groups survive artifact rejection in both
    sessions.
    """
    def _by_group_mean(vectors: list[ClassicalFeatureVector]) -> dict[tuple[str, str], float]:
        by_group: dict[tuple[str, str], list[float]] = {}
        for v in vectors:
            if feature_name in v.features:
                key = (v.condition, v.stimulus_id)
                by_group.setdefault(key, []).append(v.features[feature_name])
        return {k: float(np.mean(vals)) for k, vals in by_group.items() if vals}

    a = _by_group_mean(vectors_session_a)
    b = _by_group_mean(vectors_session_b)
    shared = sorted(set(a) & set(b))
    if len(shared) < min_shared_groups:
        return None
    a_vals = np.array([a[k] for k in shared])
    b_vals = np.array([b[k] for k in shared])
    if a_vals.std() == 0 or b_vals.std() == 0:
        return None
    return float(np.corrcoef(a_vals, b_vals)[0, 1])


def precue_postcue_discrimination(
    precue_vectors: list[ClassicalFeatureVector], postcue_vectors: list[ClassicalFeatureVector],
    feature_name: str,
) -> float:
    """Negative-control diagnostic (H1): |mean(post-cue) - mean(pre-cue)| for
    one feature, in units of the pooled standard deviation (a Cohen's-d-like
    effect size). A near-zero value means the feature carries no more
    information post-cue than pre-cue — the falsification test this feeds
    into (Commit 7, falsification test 1) expects this to be non-trivial for
    genuinely stimulus-driven features and near-zero for artifacts of the
    pipeline itself."""
    pre = np.array([v.features[feature_name] for v in precue_vectors if feature_name in v.features])
    post = np.array([v.features[feature_name] for v in postcue_vectors if feature_name in v.features])
    if len(pre) < 2 or len(post) < 2:
        return 0.0
    pooled_std = np.sqrt((pre.var() + post.var()) / 2)
    if pooled_std == 0:
        return 0.0
    return float(abs(post.mean() - pre.mean()) / pooled_std)


def build_precue_trials(perception_trials: list) -> list:
    """Construct pre-cue pseudo-trials for the negative control above: the
    fixation window immediately preceding each perception trial's onset,
    same duration as the perception phase it precedes. Reuses
    `NeuralTrialManifest` with `condition="precue"` and a synthetic
    `trial_id` suffix so it is never mistaken for a real analyzable
    condition — `preprocess_recording` treats it like any other trial phase
    (subject to the same artifact rejection), but callers must never feed
    "precue" epochs into H2/H3 confirmatory feature sets."""
    from app.research.neural.manifests import NeuralTrialManifest

    precue_trials = []
    for t in perception_trials:
        precue_onset = t.event_onset - t.event_duration
        if precue_onset < 0:
            continue
        precue_trials.append(NeuralTrialManifest(
            dataset_id=t.dataset_id, dataset_version=t.dataset_version,
            participant_id=t.participant_id, session_id=t.session_id, run_id=t.run_id,
            trial_id=t.trial_id, condition="precue", stimulus_id=t.stimulus_id,
            event_onset=precue_onset, event_duration=t.event_duration,
            behavioral_target=None, subjective_target=None,
            channel_names=t.channel_names, sampling_rate=t.sampling_rate,
            source_file_hash=t.source_file_hash,
        ))
    return precue_trials


def signal_quality_target_correlation(
    vectors: list[ClassicalFeatureVector], quality_feature_name: str, targets: list[float | None],
) -> float | None:
    """Negative control (H2-adjacent): correlation between a pure signal-
    quality proxy (e.g. broadband power, unrelated to stimulus content) and
    the behavioral target. A high correlation here would indicate the
    primary analysis risks confounding "the participant's neural signal was
    just noisier/cleaner" with "the neural signal carries content-relevant
    information" — this must stay near zero, not be the source of any H2
    incremental-validity claim."""
    paired = [
        (v.features[quality_feature_name], t)
        for v, t in zip(vectors, targets)
        if quality_feature_name in v.features and t is not None
    ]
    if len(paired) < 6:
        return None
    quality = np.array([p[0] for p in paired])
    target = np.array([p[1] for p in paired])
    if quality.std() == 0 or target.std() == 0:
        return None
    return float(np.corrcoef(quality, target)[0, 1])

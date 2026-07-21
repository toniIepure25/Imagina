"""Provenance-aware feature-variant system for C1 real-data falsification
closure (tests 2, 4, 5, 7).

Every variant is derived from the SAME retained EEG epochs, trial identities,
and behavioral records the accepted primary analysis used (see
`run_c1_confirmatory.py`) -- only the feature-construction step differs.
None of these variants replace, retune, or optimize the primary analysis;
they exist solely to falsify it. A variant record's `variant_id` and full
provenance chain make it impossible to silently mistake a control's output
for the primary confirmatory result.

Channel-label permutation is generated from a fixed seed registry
(`CHANNEL_PERMUTATION_SEEDS`), committed here before any permuted result was
inspected, per C1_ANALYSIS_SPEC.md's leakage-safe permutation requirement.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.signal import welch

from app.research.neural.features import extract_classical_features
from app.research.neural.preprocessing import FRONTAL_PROXY_CHANNELS

VARIANTS_VERSION = "1.0.0"

VARIANT_IDS = (
    "aligned_full",
    "temporally_shifted_precue",
    "temporally_shifted_late",
    "channel_group_permuted",
    "frontal_proxy_only",
    "signal_quality_only",
)

# Fixed permutation-seed registry, committed before any permuted result was
# inspected (C1_ANALYSIS_SPEC.md leakage-safe permutation requirement). Five
# independent deterministic permutations give a small distribution to compare
# the correctly-mapped result against, without implying any particular
# "number of seeds needed" beyond a modest, prespecified count.
CHANNEL_PERMUTATION_SEEDS: tuple[int, ...] = (101, 202, 303, 404, 505)

# One full imagery-phase-duration (4.0s, trigger_codebook.IMAGERY_PHASE_DURATION_S)
# after the imagery phase ends -- displaced from the prespecified imagery-locked
# interval, landing in the immediate post-imagery/inter-trial interval, while
# reusing preprocess_recording's existing out-of-recording-bounds exclusion for
# any trial where this window would run past the end of the recording.
LATE_SHIFT_OFFSET_S = 4.0


@dataclass(frozen=True)
class FeatureVariantRecord:
    """One trial's feature vector under a named variant construction, with
    full provenance back to the source epoch and code state."""
    variant_id: str
    variant_version: str
    source_epoch_hash: str
    channel_selection: tuple[str, ...]
    temporal_window: tuple[float, float]
    feature_names: tuple[str, ...]
    feature_hash: str
    participant_id: str
    session_id: str
    trial_id: str
    code_sha: str
    created_at: str
    features: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["channel_selection"] = list(self.channel_selection)
        d["feature_names"] = list(self.feature_names)
        return d

    def feature_vector(self) -> np.ndarray:
        return np.array([self.features[name] for name in self.feature_names])


def _epoch_hash(epoch: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(epoch).tobytes()).hexdigest()


def _feature_hash(features: dict[str, float]) -> str:
    payload = ",".join(f"{k}={v:.12g}" for k, v in sorted(features.items()))
    return hashlib.sha256(payload.encode()).hexdigest()


def _make_record(
    variant_id: str, epoch: np.ndarray, channel_selection: list[str], temporal_window: tuple[float, float],
    features: dict[str, float], participant_id: str, session_id: str, trial_id: str, code_sha: str,
) -> FeatureVariantRecord:
    feature_names = tuple(sorted(features.keys()))
    return FeatureVariantRecord(
        variant_id=variant_id, variant_version=VARIANTS_VERSION,
        source_epoch_hash=_epoch_hash(epoch), channel_selection=tuple(channel_selection),
        temporal_window=temporal_window, feature_names=feature_names,
        feature_hash=_feature_hash(features), participant_id=participant_id, session_id=session_id,
        trial_id=trial_id, code_sha=code_sha, created_at=datetime.now(timezone.utc).isoformat(),
        features=features,
    )


def permute_channel_labels(channel_names: list[str], seed: int) -> list[str]:
    """Deterministically permute channel LABELS (not the epoch's row data).
    Passing the permuted label list back into `extract_classical_features`
    resolves each frozen anatomical group (frontal/central/posterior) to the
    WRONG physical channel's row -- breaking anatomical spatial organization
    while reusing the identical epoch array and identical extraction code, as
    required (C1 spec Test 4: 'must break anatomical spatial organization,'
    not just shuffle the final feature columns after the fact)."""
    rng = np.random.RandomState(seed)
    permuted = list(channel_names)
    rng.shuffle(permuted)
    return permuted


def build_full_channel_variant(
    epoch: np.ndarray, sfreq: float, channel_names: list[str],
    participant_id: str, session_id: str, trial_id: str, code_sha: str,
    variant_id: str = "aligned_full", condition: str = "imagery",
    temporal_window: tuple[float, float] = (2.0, 6.0),
) -> FeatureVariantRecord:
    """Full-channel classical feature construction (identical to the primary
    confirmatory analysis' feature extraction) over an arbitrary temporal
    window's retained epoch. `variant_id`/`condition`/`temporal_window` let
    the same extraction path serve `aligned_full` (the reference variant, the
    identical primary-analysis construction), and both temporal controls
    (`temporally_shifted_precue`, `temporally_shifted_late`) -- only the
    epoch's SOURCE WINDOW differs between these, never the feature
    construction, per C1 spec Test 2's 'only neural temporal alignment
    differs' requirement."""
    fv = extract_classical_features(epoch, sfreq, channel_names, trial_id=trial_id, condition=condition)
    return _make_record(
        variant_id, epoch, channel_names, temporal_window, fv.features,
        participant_id, session_id, trial_id, code_sha,
    )


def build_aligned_full_variant(
    epoch: np.ndarray, sfreq: float, channel_names: list[str],
    participant_id: str, session_id: str, trial_id: str, code_sha: str,
    temporal_window: tuple[float, float] = (2.0, 6.0),
) -> FeatureVariantRecord:
    """The reference variant: identical feature construction to the primary
    confirmatory analysis, over the identical retained epoch. Exists so every
    control below can be reported as a difference against this SAME-provenance
    baseline, not against a separately-recomputed number."""
    return build_full_channel_variant(
        epoch, sfreq, channel_names, participant_id, session_id, trial_id, code_sha,
        variant_id="aligned_full", condition="imagery", temporal_window=temporal_window,
    )


def build_channel_permuted_variant(
    epoch: np.ndarray, sfreq: float, channel_names: list[str], seed: int,
    participant_id: str, session_id: str, trial_id: str, code_sha: str,
    temporal_window: tuple[float, float] = (2.0, 6.0),
) -> FeatureVariantRecord:
    permuted_names = permute_channel_labels(channel_names, seed)
    fv = extract_classical_features(epoch, sfreq, permuted_names, trial_id=trial_id, condition="imagery")
    return _make_record(
        f"channel_group_permuted_seed{seed}", epoch, permuted_names, temporal_window, fv.features,
        participant_id, session_id, trial_id, code_sha,
    )


def build_frontal_proxy_variant(
    epoch: np.ndarray, sfreq: float, channel_names: list[str],
    participant_id: str, session_id: str, trial_id: str, code_sha: str,
    temporal_window: tuple[float, float] = (2.0, 6.0),
) -> FeatureVariantRecord:
    idx = [i for i, c in enumerate(channel_names) if c.upper() in FRONTAL_PROXY_CHANNELS]
    restricted_epoch = epoch[idx, :]
    restricted_names = [channel_names[i] for i in idx]
    fv = extract_classical_features(restricted_epoch, sfreq, restricted_names, trial_id=trial_id, condition="imagery")
    return _make_record(
        "frontal_proxy_only", restricted_epoch, restricted_names, temporal_window, fv.features,
        participant_id, session_id, trial_id, code_sha,
    )


def _spectral_flatness(epoch: np.ndarray, sfreq: float) -> float:
    """Wiener entropy: geometric mean / arithmetic mean of the channel-averaged
    PSD. Near 1.0 for white-noise-like spectra, near 0.0 for tonal/peaked
    spectra -- a pure signal-shape descriptor, no stimulus/content information."""
    nperseg = min(epoch.shape[-1], int(sfreq * 2))
    if nperseg < 4:
        return 0.0
    _freqs, psd = welch(epoch, fs=sfreq, nperseg=nperseg, axis=-1)
    psd_mean = psd.mean(axis=0) if psd.ndim > 1 else psd
    psd_mean = np.clip(psd_mean, 1e-20, None)
    geo_mean = float(np.exp(np.mean(np.log(psd_mean))))
    arith_mean = float(psd_mean.mean())
    return geo_mean / arith_mean if arith_mean > 0 else 0.0


def extract_quality_only_features(
    epoch: np.ndarray, sfreq: float, rejection_threshold_v: float,
    n_missing_channels: int, neighboring_trial_rejection_rate: float,
    recording_retained_fraction: float,
) -> dict[str, float]:
    """Strictly non-content, outcome-independent signal-quality features
    (C1 spec Test 7). Deliberately excludes anything stimulus-locked,
    content/category-derived, anatomically content-grouped (frontal vs
    posterior), or vividness-derived -- only generic recording-quality
    descriptors that could differ across participants purely due to signal
    hygiene, never due to what was perceived or imagined."""
    peak_to_peak = epoch.max(axis=1) - epoch.min(axis=1)
    return {
        "quality__mean_peak_to_peak": float(peak_to_peak.mean()),
        "quality__max_peak_to_peak": float(peak_to_peak.max()),
        "quality__broadband_variance": float(epoch.var()),
        "quality__channelwise_variance_mean": float(epoch.var(axis=1).mean()),
        "quality__channelwise_variance_std": float(epoch.var(axis=1).std()),
        "quality__spectral_flatness": _spectral_flatness(epoch, sfreq),
        "quality__artifact_threshold_proximity": (
            float(peak_to_peak.max() / rejection_threshold_v) if rejection_threshold_v else 0.0
        ),
        "quality__n_missing_channels": float(n_missing_channels),
        "quality__neighboring_trial_rejection_rate": float(neighboring_trial_rejection_rate),
        "quality__recording_retained_fraction": float(recording_retained_fraction),
    }


def build_quality_only_variant(
    epoch: np.ndarray, sfreq: float, channel_names: list[str], rejection_threshold_v: float,
    n_missing_channels: int, neighboring_trial_rejection_rate: float, recording_retained_fraction: float,
    participant_id: str, session_id: str, trial_id: str, code_sha: str,
    temporal_window: tuple[float, float] = (2.0, 6.0),
) -> FeatureVariantRecord:
    features = extract_quality_only_features(
        epoch, sfreq, rejection_threshold_v, n_missing_channels,
        neighboring_trial_rejection_rate, recording_retained_fraction,
    )
    return _make_record(
        "signal_quality_only", epoch, channel_names, temporal_window, features,
        participant_id, session_id, trial_id, code_sha,
    )


def neighboring_trial_rejection_rate(
    trial_index: int, all_trial_indices: list[int], kept_trial_indices: set[int], window: int = 5,
) -> float:
    """Fraction of nearby trials (within +/- `window` trial indices in the
    SAME recording) that were excluded during artifact rejection -- a
    recording-context quality signal, independent of this trial's own content."""
    neighbors = [i for i in all_trial_indices if i != trial_index and abs(i - trial_index) <= window]
    if not neighbors:
        return 0.0
    rejected = sum(1 for i in neighbors if i not in kept_trial_indices)
    return rejected / len(neighbors)


def build_late_shift_trials(imagery_trials: list) -> list:
    """Construct 'late-shift' pseudo-trials for falsification test 2's
    second temporal control: a window displaced `LATE_SHIFT_OFFSET_S` after
    each imagery trial's own onset (landing just past the prespecified
    imagery-locked interval, in the immediate post-imagery/inter-trial
    interval), same duration as the imagery phase it follows. Mirrors
    `features.build_precue_trials`'s construction (same `NeuralTrialManifest`
    reuse pattern, same "never mistaken for a real analyzable condition"
    convention via a distinct `condition` value), just shifted forward instead
    of backward. `preprocess_recording`'s existing out-of-recording-bounds
    check gracefully excludes any trial for which this window runs past the
    end of the recording -- no separate bounds logic needed here."""
    from app.research.neural.manifests import NeuralTrialManifest

    late_shift_trials = []
    for t in imagery_trials:
        late_onset = t.event_onset + LATE_SHIFT_OFFSET_S
        late_shift_trials.append(NeuralTrialManifest(
            dataset_id=t.dataset_id, dataset_version=t.dataset_version,
            participant_id=t.participant_id, session_id=t.session_id, run_id=t.run_id,
            trial_id=t.trial_id, condition="late_shift", stimulus_id=t.stimulus_id,
            event_onset=late_onset, event_duration=t.event_duration,
            behavioral_target=None, subjective_target=None,
            channel_names=t.channel_names, sampling_rate=t.sampling_rate,
            source_file_hash=t.source_file_hash,
        ))
    return late_shift_trials

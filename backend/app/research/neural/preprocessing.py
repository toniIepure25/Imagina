"""Fold-safe EEG preprocessing and QC for Scientific Gate C1.

All parameters here are fixed constants applied identically to every
recording, regardless of which outer/inner fold that recording's participant
falls into — nothing in this module is fit on data (no adaptive thresholds,
no cross-trial normalization, no label-informed component selection). That
keeps it safe to run once per recording, ahead of and independent from the
nested-CV split in Commit 7. The only per-recording "fitting" step (ICA) is
fit strictly within that one recording's own continuous data, never using
labels, other participants, or other recordings — see `PreprocessingConfig`
and `run_ica` below for the precise boundary.

Steps NOT in this module because they legitimately require fold-awareness:
normalization/z-scoring, ICA *component selection* driven by an outcome
label, PCA, spatial filters (CSP/FBCSP), feature selection, and imputation.
Those belong to Commit 4/5 feature and model code, fit only inside the outer-
training participants' folds, per `C1_PROTOCOL.md` Section 9.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

PREPROCESSING_VERSION = "1.0.0"

EXPECTED_YOTO_CHANNELS = (
    "FP1", "FP2", "F7", "F3", "FZ", "F4", "F8", "FT7", "FC3", "FCZ",
    "FC4", "FT8", "T7", "C3", "CZ", "C4", "T8", "TP7", "CP3", "CPZ",
    "CP4", "TP8", "P7", "P3", "PZ", "P4", "P8", "O1", "OZ", "O2",
)

# Frontal channels used as an ocular-artifact proxy negative control
# (falsification test 5) — ds005815 has no dedicated EOG channel, a
# documented limitation (see C1_PROTOCOL.md Section 11).
FRONTAL_PROXY_CHANNELS = ("FP1", "FP2", "F7", "F3", "FZ", "F4", "F8")

POSTERIOR_CHANNELS = ("P7", "P3", "PZ", "P4", "P8", "O1", "OZ", "O2")


@dataclass(frozen=True)
class PreprocessingConfig:
    """Fixed, prespecified preprocessing parameters — never fit from data."""
    notch_freq_hz: float = 60.0
    band_pass_low_hz: float = 0.5
    band_pass_high_hz: float = 40.0
    resample_to_hz: float = 250.0
    reference: str = "average"
    baseline_window_s: tuple[float, float] = (-0.5, 0.0)
    reject_peak_to_peak_v: float = 150e-6  # 150 microvolts, standard EEG artifact threshold
    run_ica: bool = True
    ica_n_components: float = 0.99  # fraction of variance, not a label-informed count
    version: str = PREPROCESSING_VERSION


@dataclass(frozen=True)
class PreprocessingManifest:
    dataset_id: str
    participant_id: str
    session_id: str
    run_id: str
    raw_hash: str
    preprocessing_version: str
    filter_parameters: dict[str, float]
    reference: str
    epoch_window_s: tuple[float, float]
    baseline_window_s: tuple[float, float]
    rejection_threshold_v: float
    included_channels: tuple[str, ...]
    excluded_channels: tuple[str, ...]
    included_trials: tuple[str, ...]
    excluded_trials: tuple[str, ...]
    exclusion_reasons: dict[str, str]
    output_hash: str

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["included_channels"] = list(self.included_channels)
        d["excluded_channels"] = list(self.excluded_channels)
        d["included_trials"] = list(self.included_trials)
        d["excluded_trials"] = list(self.excluded_trials)
        return d


@dataclass
class QCReport:
    dataset_id: str
    participant_id: str
    session_id: str
    n_trials_total: int
    n_trials_retained: int
    retained_fraction: float
    bad_channels: tuple[str, ...]
    artifact_fraction_by_condition: dict[str, float]
    class_balance: dict[str, int]
    temporal_drift_corr: float | None
    block_order_confound_flag: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["bad_channels"] = list(self.bad_channels)
        d["notes"] = list(self.notes)
        return d


def validate_channels(
    ch_names: list[str], expected: tuple[str, ...] = EXPECTED_YOTO_CHANNELS,
) -> tuple[list[str], list[str]]:
    """Return (present_expected, missing_expected). Missing channels trigger
    the missing-channel policy in `preprocess_recording`: excluded, never
    silently zero-filled or interpolated without recording the fact."""
    have = {c.upper() for c in ch_names}
    present = [c for c in expected if c in have]
    missing = [c for c in expected if c not in have]
    return present, missing


def _content_hash(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def preprocess_recording(
    raw,  # mne.io.Raw
    trials: list,  # list[NeuralTrialManifest]
    raw_hash: str,
    config: PreprocessingConfig = PreprocessingConfig(),
) -> tuple[dict[str, np.ndarray], list, PreprocessingManifest]:
    """Apply the fixed preprocessing pipeline and extract epochs for every
    trial phase. Returns (epochs_by_condition, kept_trials, manifest), where
    epochs_by_condition maps e.g. "perception" -> array[n_trials, n_channels,
    n_samples] and "imagery" -> array[n_trials, n_channels, n_samples] with
    its own (longer) n_samples — perception and imagery phases have
    different fixed durations and are never forced into one shared-length
    array. Never fits any parameter from this recording's own trial outcomes
    or from other recordings.
    """
    import mne

    present_channels, missing_channels = validate_channels(raw.ch_names)
    exclusion_reasons: dict[str, str] = {}
    for ch in missing_channels:
        exclusion_reasons[f"channel:{ch}"] = "missing_channel_policy: expected channel absent from recording"

    raw = raw.copy().pick(present_channels)
    try:
        raw.set_montage("standard_1020", match_case=False, on_missing="warn", verbose="ERROR")
    except Exception as e:  # pragma: no cover - defensive, montage issues are rare with standard 10-20 names
        exclusion_reasons["montage"] = f"montage_validation_failed: {e}"

    raw.load_data(verbose="ERROR")
    raw.notch_filter(config.notch_freq_hz, verbose="ERROR")
    raw.filter(config.band_pass_low_hz, config.band_pass_high_hz, verbose="ERROR")
    raw.resample(config.resample_to_hz, verbose="ERROR")
    if config.reference == "average":
        raw.set_eeg_reference("average", verbose="ERROR")

    if config.run_ica:
        # ICA is fit strictly on this one recording's own continuous data —
        # no labels, no other participants, no other recordings. Component
        # rejection uses a fixed EOG-proxy correlation threshold (frontal
        # channels), not an outcome-label-driven selection.
        ica = mne.preprocessing.ICA(n_components=config.ica_n_components, random_state=42, verbose="ERROR")
        ica.fit(raw, verbose="ERROR")
        try:
            eog_indices, _scores = ica.find_bads_eog(raw, ch_name=list(FRONTAL_PROXY_CHANNELS), verbose="ERROR")
            ica.exclude = eog_indices
        except Exception:
            pass  # no reliable EOG-proxy correlation found; keep all components
        ica.apply(raw, verbose="ERROR")

    # Perception (2s) and imagery (4s) phases have different, condition-fixed
    # durations — they are never zero-padded to a shared length (that would
    # inject an artificial signal-to-zero discontinuity that trips the
    # peak-to-peak artifact rejection on physiologically clean data). Epochs
    # are grouped and stacked per condition instead.
    epochs_by_condition: dict[str, list[np.ndarray]] = {}
    kept_trials: list = []
    excluded_trial_ids: list[str] = []

    sfreq = raw.info["sfreq"]
    data = raw.get_data()

    # Baseline correction is relative to the trial's perception-phase onset
    # (the earliest, stimulus-locked event) so both the perception and the
    # later imagery phase of the same physical trial share one pre-stimulus
    # reference, per standard ERP convention.
    trial_reference_onset: dict[str, float] = {
        t.trial_id: t.event_onset for t in trials if t.condition == "perception"
    }
    baseline_start_s, baseline_end_s = config.baseline_window_s

    for t in trials:
        start_sample = int(round(t.event_onset * sfreq))
        n_samples = int(round(t.event_duration * sfreq))
        if start_sample < 0 or start_sample + n_samples > data.shape[1]:
            excluded_trial_ids.append(t.trial_id + f":{t.condition}")
            exclusion_reasons[f"trial:{t.trial_id}:{t.condition}"] = "epoch_out_of_recording_bounds"
            continue

        epoch = data[:, start_sample:start_sample + n_samples]

        ref_onset = trial_reference_onset.get(t.trial_id, t.event_onset)
        baseline_start_sample = int(round((ref_onset + baseline_start_s) * sfreq))
        baseline_end_sample = int(round((ref_onset + baseline_end_s) * sfreq))
        if 0 <= baseline_start_sample < baseline_end_sample <= data.shape[1]:
            baseline_mean = data[:, baseline_start_sample:baseline_end_sample].mean(axis=1, keepdims=True)
            epoch = epoch - baseline_mean
        else:
            exclusion_reasons.setdefault(
                f"trial:{t.trial_id}:{t.condition}:baseline",
                "baseline_window_out_of_recording_bounds: epoch retained uncorrected",
            )

        peak_to_peak = epoch.max(axis=1) - epoch.min(axis=1)
        if np.any(peak_to_peak > config.reject_peak_to_peak_v):
            excluded_trial_ids.append(t.trial_id + f":{t.condition}")
            exclusion_reasons[f"trial:{t.trial_id}:{t.condition}"] = (
                f"artifact_rejection: peak-to-peak amplitude exceeded {config.reject_peak_to_peak_v}V"
            )
            continue

        epochs_by_condition.setdefault(t.condition, []).append(epoch)
        kept_trials.append(t)

    epochs_array = {
        cond: np.stack(eps, axis=0) for cond, eps in epochs_by_condition.items()
    }
    # Perception and imagery epochs have different shapes and cannot be
    # concatenated into one array; hash each condition's array independently
    # and combine the digests so the manifest still carries one output_hash.
    per_condition_hashes = "".join(
        _content_hash(epochs_array[cond]) for cond in sorted(epochs_array)
    )
    output_hash = hashlib.sha256(per_condition_hashes.encode()).hexdigest()

    manifest = PreprocessingManifest(
        dataset_id=trials[0].dataset_id if trials else "",
        participant_id=trials[0].participant_id if trials else "",
        session_id=trials[0].session_id if trials else "",
        run_id=trials[0].run_id if trials else "",
        raw_hash=raw_hash,
        preprocessing_version=config.version,
        filter_parameters={
            "notch_freq_hz": config.notch_freq_hz,
            "band_pass_low_hz": config.band_pass_low_hz,
            "band_pass_high_hz": config.band_pass_high_hz,
            "resample_to_hz": config.resample_to_hz,
        },
        reference=config.reference,
        epoch_window_s=(0.0, max((t.event_duration for t in trials), default=0.0)),
        baseline_window_s=config.baseline_window_s,
        rejection_threshold_v=config.reject_peak_to_peak_v,
        included_channels=tuple(present_channels),
        excluded_channels=tuple(missing_channels),
        included_trials=tuple(f"{t.trial_id}:{t.condition}" for t in kept_trials),
        excluded_trials=tuple(excluded_trial_ids),
        exclusion_reasons=exclusion_reasons,
        output_hash=output_hash,
    )
    return epochs_array, kept_trials, manifest


def build_qc_report(
    dataset_id: str, participant_id: str, session_id: str,
    all_trials: list, kept_trials: list, manifest: PreprocessingManifest,
) -> QCReport:
    n_total = len(all_trials)
    n_kept = len(kept_trials)

    by_condition_total: dict[str, int] = {}
    by_condition_excluded: dict[str, int] = {}
    for t in all_trials:
        by_condition_total[t.condition] = by_condition_total.get(t.condition, 0) + 1
    kept_keys = {(t.trial_id, t.condition) for t in kept_trials}
    for t in all_trials:
        if (t.trial_id, t.condition) not in kept_keys:
            by_condition_excluded[t.condition] = by_condition_excluded.get(t.condition, 0) + 1

    artifact_fraction_by_condition = {
        cond: by_condition_excluded.get(cond, 0) / total
        for cond, total in by_condition_total.items()
    }

    class_balance: dict[str, int] = {}
    for t in kept_trials:
        class_balance[t.stimulus_id] = class_balance.get(t.stimulus_id, 0) + 1

    onsets_by_trial_index = [t.event_onset for t in kept_trials]
    temporal_drift_corr = None
    if len(onsets_by_trial_index) >= 3:
        onsets_with_target = [
            (o, t.behavioral_target)
            for o, t in zip(onsets_by_trial_index, kept_trials)
            if t.behavioral_target is not None
        ]
        if len(onsets_with_target) >= 3:
            onsets_arr = np.array([o for o, _ in onsets_with_target])
            targets_arr = np.array([v for _, v in onsets_with_target])
            if onsets_arr.std() > 0 and targets_arr.std() > 0:
                temporal_drift_corr = float(np.corrcoef(onsets_arr, targets_arr)[0, 1])

    # Block/order confound flag: True if any single stimulus_id's trials are
    # all clustered in one contiguous third of the recording (a coarse,
    # conservative proxy — refined empirically as more sessions are ingested).
    block_order_confound_flag = False
    if kept_trials:
        span = max(onsets_by_trial_index) - min(onsets_by_trial_index) or 1.0
        by_stim: dict[str, list[float]] = {}
        for t in kept_trials:
            by_stim.setdefault(t.stimulus_id, []).append(t.event_onset)
        for onsets in by_stim.values():
            if len(onsets) < 2:
                continue
            rel = [(o - min(onsets_by_trial_index)) / span for o in onsets]
            if max(rel) - min(rel) < 0.34:
                block_order_confound_flag = True
                break

    return QCReport(
        dataset_id=dataset_id, participant_id=participant_id, session_id=session_id,
        n_trials_total=n_total, n_trials_retained=n_kept,
        retained_fraction=(n_kept / n_total) if n_total else 0.0,
        bad_channels=manifest.excluded_channels,
        artifact_fraction_by_condition=artifact_fraction_by_condition,
        class_balance=class_balance,
        temporal_drift_corr=temporal_drift_corr,
        block_order_confound_flag=block_order_confound_flag,
    )


def write_qc_json(report: QCReport, path: str) -> None:
    with open(path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

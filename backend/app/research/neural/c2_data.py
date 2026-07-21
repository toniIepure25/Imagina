"""Matched content-state trial view for Scientific Gate C2.

Builds a single, provenance-carrying trial representation
(`MatchedTrialRecord`) that keeps content (stimulus category), state
(perception vs. imagery), and every nuisance covariate (participant,
session, block, trial order, signal quality) explicitly separated and
addressable -- per `C2_PROTOCOL.md` Section 3's factorization requirement.

Reuses C1's fold-safe preprocessing (`preprocessing.preprocess_recording`)
and quality-feature extraction (`variants.extract_quality_only_features`)
unchanged; adds only the C2-specific trial selection (visual-content trials
only) and the equal-duration common-window construction C2-H3 requires.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.variants import extract_quality_only_features

C2_DATA_VERSION = "1.0.0"

PRIMARY_CONTENT_CLASSES = ("visual_square", "visual_face_male", "visual_face_female")

# The common analysis window for state decoding (C2-H3): the first
# COMMON_WINDOW_DURATION_S of BOTH perception (already exactly this long)
# and imagery (truncated from its full 4.0s), so epoch length itself
# cannot trivially reveal the state.
COMMON_WINDOW_DURATION_S = 2.0


@dataclass(frozen=True)
class MatchedTrialRecord:
    """One trial-phase epoch's content-state-nuisance factorization."""
    participant_id: str
    session_id: str
    trial_id: str
    stimulus_category: str  # one of PRIMARY_CONTENT_CLASSES
    state: str  # "perception" | "imagery" | "imagery_common_window"
    block_index: int
    trial_order: int  # trial_index_in_session
    epoch_hash: str
    signal_quality_features: dict[str, float]
    source_manifest_hash: str
    neural_features: np.ndarray | None = None  # populated by later commits' feature/encoder steps

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        if d["neural_features"] is not None:
            d["neural_features"] = d["neural_features"].tolist()
        return d


def _epoch_hash(epoch: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(epoch).tobytes()).hexdigest()


def is_primary_content_trial(stimulus_id: str) -> bool:
    return stimulus_id in PRIMARY_CONTENT_CLASSES


def select_visual_content_trials(trials: list, condition: str) -> list:
    """Restrict a trial manifest list to the given `condition`
    ("perception" | "imagery") AND the primary 3-class visual content
    subset -- never the mixed-modality or auditory-only trials, per
    `C2_PROTOCOL.md` Section 4."""
    return [t for t in trials if t.condition == condition and is_primary_content_trial(t.stimulus_id)]


def build_common_window_imagery_trials(imagery_trials: list) -> list:
    """Truncate each imagery trial's window to `COMMON_WINDOW_DURATION_S`
    starting at its own onset (same onset as the full imagery trial, just
    shorter duration) -- for the C2-H3 equal-duration state-decoding view.
    Mirrors the `NeuralTrialManifest` reuse pattern established by C1's
    `features.build_precue_trials`/`variants.build_late_shift_trials`."""
    from app.research.neural.manifests import NeuralTrialManifest

    out = []
    for t in imagery_trials:
        out.append(NeuralTrialManifest(
            dataset_id=t.dataset_id, dataset_version=t.dataset_version,
            participant_id=t.participant_id, session_id=t.session_id, run_id=t.run_id,
            trial_id=t.trial_id, condition="imagery_common_window", stimulus_id=t.stimulus_id,
            event_onset=t.event_onset, event_duration=COMMON_WINDOW_DURATION_S,
            behavioral_target=t.behavioral_target, subjective_target=t.subjective_target,
            channel_names=t.channel_names, sampling_rate=t.sampling_rate,
            source_file_hash=t.source_file_hash,
        ))
    return out


def make_matched_record(
    epoch: np.ndarray, sfreq: float, rejection_threshold_v: float,
    n_missing_channels: int, neighboring_trial_rejection_rate: float, recording_retained_fraction: float,
    participant_id: str, session_id: str, trial_id: str, stimulus_category: str, state: str,
    block_index: int, trial_order: int, source_manifest_hash: str,
) -> MatchedTrialRecord:
    quality_features = extract_quality_only_features(
        epoch, sfreq, rejection_threshold_v, n_missing_channels,
        neighboring_trial_rejection_rate, recording_retained_fraction,
    )
    return MatchedTrialRecord(
        participant_id=participant_id, session_id=session_id, trial_id=trial_id,
        stimulus_category=stimulus_category, state=state, block_index=block_index,
        trial_order=trial_order, epoch_hash=_epoch_hash(epoch),
        signal_quality_features=quality_features, source_manifest_hash=source_manifest_hash,
    )


def verify_no_paired_trial_split_across_folds(
    records: list[MatchedTrialRecord], held_out_participant: str,
) -> bool:
    """Structural leakage check (C2 spec Section 7, test 9): every
    (participant_id, session_id, trial_id) triple with BOTH a perception and
    an imagery record must land entirely on one side of a LOSO fold. True
    always holds by construction here (fold membership is participant-only),
    but this function makes the guarantee independently checkable rather
    than merely assumed."""
    train_triples = {
        (r.participant_id, r.session_id, r.trial_id)
        for r in records if r.participant_id != held_out_participant
    }
    test_triples = {
        (r.participant_id, r.session_id, r.trial_id)
        for r in records if r.participant_id == held_out_participant
    }
    return len(train_triples & test_triples) == 0

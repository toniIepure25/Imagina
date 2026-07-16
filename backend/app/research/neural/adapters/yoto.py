"""ds005815 (YOTO) ingestion adapter.

Reads one BIDS raw recording (participant/session/task-task run), decodes
its trigger stream via the authoritative `trigger_codebook`, and produces a
`NeuralRecordingManifest` plus two `NeuralTrialManifest` rows per valid trial
(perception phase, imagery phase).

Behavioral target alignment (vividness): the dataset's authors publish a
per-trial vividness CSV (`Trigger_Vividness_Data.csv`, fetched via
`download.py`) that is NOT in the same row order as the raw BIDS event
stream — verified during Commit 2 by downloading sub-01/ses-1 and comparing
sequences directly (see `docs/research/C1_DATASET_CANDIDATES.md`). What DOES
match exactly, subject by subject and session by session, is the per-trigger
-code occurrence COUNT. This adapter therefore aligns behavioral_target by
(participant, session, trigger_code, occurrence-index-within-code), assuming
occurrence order within a code group is chronology-preserving in both
sources. This is a documented assumption, not a certainty — see the
"Residual risks" section of C1_DATASET_CANDIDATES.md. If this assumption is
later falsified (e.g. by an independent confound check in Commit 3 QC),
vividness must be treated as trial-count-correct but instance-uncertain, and
the H2 primary analysis must fall back to a code-conservative aggregate
target or a stopping condition per C1_PROTOCOL.md Section 10.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timezone

from app.research.neural.adapters.base import NeuralDatasetAdapter
from app.research.neural.hashing import sha256_file
from app.research.neural.manifests import NeuralRecordingManifest, NeuralTrialManifest
from app.research.neural.registry import YOTO_DESCRIPTOR
from app.research.neural.trigger_codebook import (
    IMAGERY_PHASE_DURATION_S,
    IMAGERY_PHASE_OFFSET_S,
    PERCEPTION_PHASE_DURATION_S,
    PERCEPTION_PHASE_OFFSET_S,
    decode_trigger,
)


def _bids_to_csv_subject(participant_id: str) -> str:
    """'sub-01' -> 's001', matching the authors' Trigger_Vividness_Data.csv."""
    num = int(participant_id.split("-")[1])
    return f"s{num:03d}"


def _bids_to_csv_session(session_id: str) -> str:
    """'1' -> 'session_1'."""
    return f"session_{session_id}"


def _load_vividness_index(csv_path: str) -> dict[tuple[str, str], dict[int, list[int]]]:
    """Return {(subject, session): {trigger_code: [vividness, vividness, ...]}}
    in file order, so the Nth occurrence of a code can be looked up by index."""
    index: dict[tuple[str, str], dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["Subject"], row["Session"])
            index[key][int(row["Trigger"])].append(int(row["Vividness"]))
    return index


def _read_events_tsv(path: str) -> list[tuple[float, float, int]]:
    """Return [(onset_s, duration_s, trigger_value), ...] for TrialProc rows only."""
    rows: list[tuple[float, float, int]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["trial_type"] != "TrialProc":
                continue
            value = row.get("value", "").strip()
            if not value:
                continue
            rows.append((float(row["onset"]), float(row["duration"] or 0.0), int(value)))
    return rows


class YotoAdapter(NeuralDatasetAdapter):
    dataset_id = YOTO_DESCRIPTOR.dataset_id
    dataset_version = YOTO_DESCRIPTOR.dataset_version
    adapter_version = YOTO_DESCRIPTOR.adapter_version

    def __init__(self, data_root: str, vividness_csv_path: str | None = None):
        self.data_root = data_root
        self.vividness_csv_path = vividness_csv_path or os.path.join(
            data_root, "ancillary", "Trigger_Vividness_Data.csv",
        )
        self._vividness_index: dict[tuple[str, str], dict[int, list[int]]] | None = None

    def _vividness_for(self, participant_id: str, session_id: str) -> dict[int, list[int]]:
        if self._vividness_index is None:
            self._vividness_index = _load_vividness_index(self.vividness_csv_path)
        key = (_bids_to_csv_subject(participant_id), _bids_to_csv_session(session_id))
        return self._vividness_index.get(key, {})

    def ingest_recording(
        self, participant_id: str, session_id: str, run_id: str = "task",
    ) -> tuple[NeuralRecordingManifest, list[NeuralTrialManifest]]:
        rec_dir = os.path.join(self.data_root, participant_id, f"ses-{session_id}", "eeg")
        stem = f"{participant_id}_ses-{session_id}_task-{run_id}"
        vhdr_path = os.path.join(rec_dir, f"{stem}_eeg.vhdr")
        eeg_path = os.path.join(rec_dir, f"{stem}_eeg.eeg")
        events_path = os.path.join(rec_dir, f"{stem}_events.tsv")

        import mne
        raw = mne.io.read_raw_brainvision(vhdr_path, preload=False, verbose="ERROR")
        channel_names = tuple(raw.ch_names)
        sampling_rate = float(raw.info["sfreq"])
        n_samples = int(raw.n_times)
        duration_s = n_samples / sampling_rate

        source_file_hash = sha256_file(eeg_path)

        metadata_repairs: list[str] = []
        # The BIDS eeg.json sidecar's TaskDescription/RecordingDuration for
        # this task run is known (verified in Commit 2) to have been copied
        # from a different (resting-state) run; this adapter never reads
        # duration/description from that sidecar, only from the raw file
        # itself, and records the repair for provenance.
        metadata_repairs.append(
            "eeg.json TaskDescription/RecordingDuration ignored (copied from a "
            "resting-state run in the source dataset); duration/channels read "
            "from the raw BrainVision header instead."
        )

        trial_events = _read_events_tsv(events_path)
        vividness_by_code = self._vividness_for(participant_id, session_id)
        occurrence_counter: dict[int, int] = defaultdict(int)

        trials: list[NeuralTrialManifest] = []
        exclusions: list[str] = []

        for onset, _duration, code in trial_events:
            meaning = decode_trigger(code)
            if meaning is None:
                exclusions.append(f"onset={onset}s: unresolved trigger code {code}")
                continue

            occurrence_index = occurrence_counter[code]
            occurrence_counter[code] += 1
            ratings = vividness_by_code.get(code, [])
            vividness = ratings[occurrence_index] if occurrence_index < len(ratings) else None
            if vividness is None:
                exclusions.append(
                    f"onset={onset}s trigger={code}: no vividness rating at "
                    f"occurrence index {occurrence_index} (behavioral_target excluded, "
                    f"EEG epochs still retained for H1/H3/H4 exploratory use)"
                )

            trial_id = f"{participant_id}_ses-{session_id}_{run_id}_t{len(trials) // 2:04d}_code{code}"

            trials.append(NeuralTrialManifest(
                dataset_id=self.dataset_id, dataset_version=self.dataset_version,
                participant_id=participant_id, session_id=session_id, run_id=run_id,
                trial_id=trial_id, condition="perception", stimulus_id=meaning.stimulus_id,
                event_onset=onset + PERCEPTION_PHASE_OFFSET_S,
                event_duration=PERCEPTION_PHASE_DURATION_S,
                behavioral_target=float(vividness) if vividness is not None else None,
                subjective_target=None,
                channel_names=channel_names, sampling_rate=sampling_rate,
                source_file_hash=source_file_hash,
            ))
            trials.append(NeuralTrialManifest(
                dataset_id=self.dataset_id, dataset_version=self.dataset_version,
                participant_id=participant_id, session_id=session_id, run_id=run_id,
                trial_id=trial_id, condition="imagery", stimulus_id=meaning.stimulus_id,
                event_onset=onset + IMAGERY_PHASE_OFFSET_S,
                event_duration=IMAGERY_PHASE_DURATION_S,
                behavioral_target=float(vividness) if vividness is not None else None,
                subjective_target=None,
                channel_names=channel_names, sampling_rate=sampling_rate,
                source_file_hash=source_file_hash,
            ))

        recording = NeuralRecordingManifest(
            dataset_id=self.dataset_id, dataset_version=self.dataset_version,
            participant_id=participant_id, session_id=session_id, run_id=run_id,
            original_source=f"s3://openneuro.org/ds005815/{participant_id}/ses-{session_id}/eeg/",
            download_timestamp=datetime.now(timezone.utc).isoformat(),
            adapter_version=self.adapter_version, source_file_hash=source_file_hash,
            channel_names=channel_names, sampling_rate=sampling_rate,
            n_samples=n_samples, duration_s=duration_s,
            exclusions=tuple(exclusions), metadata_repairs=tuple(metadata_repairs),
        )
        return recording, trials

"""Tests for the ds005815 (YOTO) ingestion adapter.

Uses a tiny synthetic BrainVision recording (written via MNE/pybv, the same
format and code path `mne.io.read_raw_brainvision` uses for the real
dataset) plus hand-built events.tsv/vividness CSV fixtures matching the
dataset's real schema — never the actual ~114MB raw recording, which is not
committed to this repository and is not required for CI.
"""
import csv

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from app.research.neural.adapters.yoto import YotoAdapter  # noqa: E402
from app.research.neural.trigger_codebook import TRIGGER_INFO, decode_trigger  # noqa: E402


@pytest.fixture
def yoto_fixture(tmp_path):
    """Build a tiny synthetic recording + matching events.tsv + vividness CSV
    for sub-01/ses-1, using three real trigger codes (23, 24, 37)."""
    data_root = tmp_path / "ds005815"
    rec_dir = data_root / "sub-01" / "ses-1" / "eeg"
    rec_dir.mkdir(parents=True)

    sfreq = 100.0
    ch_names = ["Fp1", "Fp2", "Cz", "O1"]
    info = mne.create_info(ch_names, sfreq, ch_types="eeg")
    n_samples = int(sfreq * 20)  # 20 seconds, enough for a handful of trials
    data = np.random.RandomState(42).randn(len(ch_names), n_samples) * 1e-5
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    vhdr_path = rec_dir / "sub-01_ses-1_task-task_eeg.vhdr"
    raw.export(str(vhdr_path), fmt="brainvision", overwrite=True, verbose="ERROR")

    # Three trials: codes 23 (visual square), 24 (auditory speech-a) twice.
    events_path = rec_dir / "sub-01_ses-1_task-task_events.tsv"
    with open(events_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["onset", "duration", "trial_type", "value"])
        w.writerow(["1.0", "0.0", "startIntro", ""])
        w.writerow(["2.0", "0.0", "TrialProc", "23"])
        w.writerow(["8.0", "0.0", "TrialProc", "24"])
        w.writerow(["14.0", "0.0", "TrialProc", "24"])

    vividness_path = data_root / "ancillary" / "Trigger_Vividness_Data.csv"
    vividness_path.parent.mkdir(parents=True)
    with open(vividness_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Subject", "Session", "Trial", "Trigger", "Vividness"])
        w.writerow(["s001", "session_1", "1", "23", "4"])
        w.writerow(["s001", "session_1", "2", "24", "3"])
        w.writerow(["s001", "session_1", "3", "24", "5"])

    return str(data_root)


def test_trigger_codebook_decodes_known_codes():
    assert decode_trigger(23).stimulus_id == "visual_square"
    assert decode_trigger(23).modality == "visual"
    assert decode_trigger(37).stimulus_id == "mix_visual_auditory_face_male_speech_o"
    assert decode_trigger(37).modality == "mix"
    assert decode_trigger(24).modality == "auditory"


def test_trigger_codebook_rejects_non_trial_and_unknown_codes():
    assert decode_trigger(6) is None  # fixation marker, not a trial
    assert decode_trigger(3) is None  # resting marker
    assert decode_trigger(999) is None  # not in the authoritative table


def test_trigger_codebook_covers_all_events_tsv_range():
    # Every trigger value actually observed in the real ds005815 events.tsv
    # (21-47) must be present in the authoritative table.
    for code in range(21, 48):
        assert code in TRIGGER_INFO, f"missing decode for observed trigger {code}"


def test_adapter_ingests_recording_and_produces_two_phases_per_trial(yoto_fixture):
    adapter = YotoAdapter(data_root=yoto_fixture)
    recording, trials = adapter.ingest_recording("sub-01", "1", "task")

    assert recording.dataset_id == "ds005815"
    assert recording.channel_names == ("Fp1", "Fp2", "Cz", "O1")
    assert recording.sampling_rate == 100.0
    assert len(recording.source_file_hash) == 64  # sha256 hex digest
    assert recording.exclusions == ()

    # 3 real trials -> 2 phase rows each (perception, imagery)
    assert len(trials) == 6

    perception = [t for t in trials if t.condition == "perception"]
    imagery = [t for t in trials if t.condition == "imagery"]
    assert len(perception) == 3
    assert len(imagery) == 3

    first_trial_id = perception[0].trial_id
    matching_imagery = [t for t in imagery if t.trial_id == first_trial_id]
    assert len(matching_imagery) == 1, "perception and imagery phases of one trial share a trial_id"

    assert perception[0].stimulus_id == "visual_square"
    assert perception[0].behavioral_target == 4.0
    assert matching_imagery[0].behavioral_target == 4.0  # same trial, same target

    # imagery phase starts 2s after perception phase onset, per the frozen
    # trial-timing constants in trigger_codebook.py
    assert matching_imagery[0].event_onset - perception[0].event_onset == pytest.approx(2.0)


def test_adapter_aligns_repeated_trigger_by_occurrence_index(yoto_fixture):
    """Two trials share trigger 24; vividness must be assigned by occurrence
    order (3, then 5), not the same value twice."""
    adapter = YotoAdapter(data_root=yoto_fixture)
    _recording, trials = adapter.ingest_recording("sub-01", "1", "task")

    code24_perception = [
        t for t in trials if t.condition == "perception" and t.stimulus_id == "auditory_speech_a"
    ]
    assert len(code24_perception) == 2
    code24_perception.sort(key=lambda t: t.event_onset)
    assert code24_perception[0].behavioral_target == 3.0
    assert code24_perception[1].behavioral_target == 5.0


def test_adapter_excludes_unresolvable_trigger_without_fabricating_condition(tmp_path):
    """A trigger code absent from the authoritative table must be excluded,
    never silently assigned a guessed condition or stimulus."""
    data_root = tmp_path / "ds005815"
    rec_dir = data_root / "sub-01" / "ses-1" / "eeg"
    rec_dir.mkdir(parents=True)

    sfreq = 100.0
    info = mne.create_info(["Fp1"], sfreq, ch_types="eeg")
    data = np.zeros((1, int(sfreq * 5)))
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.export(str(rec_dir / "sub-01_ses-1_task-task_eeg.vhdr"), fmt="brainvision",
               overwrite=True, verbose="ERROR")

    events_path = rec_dir / "sub-01_ses-1_task-task_events.tsv"
    with open(events_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["onset", "duration", "trial_type", "value"])
        w.writerow(["1.0", "0.0", "TrialProc", "999"])  # not in TRIGGER_INFO

    (data_root / "ancillary").mkdir()
    with open(data_root / "ancillary" / "Trigger_Vividness_Data.csv", "w", newline="") as f:
        csv.writer(f).writerow(["Subject", "Session", "Trial", "Trigger", "Vividness"])

    adapter = YotoAdapter(data_root=str(data_root))
    recording, trials = adapter.ingest_recording("sub-01", "1", "task")

    assert trials == []
    assert len(recording.exclusions) == 1
    assert "999" in recording.exclusions[0]


def test_adapter_records_known_eeg_json_metadata_repair(yoto_fixture):
    adapter = YotoAdapter(data_root=yoto_fixture)
    recording, _trials = adapter.ingest_recording("sub-01", "1", "task")
    assert any("resting-state" in repair for repair in recording.metadata_repairs)

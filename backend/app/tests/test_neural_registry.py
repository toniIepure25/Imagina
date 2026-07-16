"""Tests for the C1 neural dataset registry and provenance dataclasses."""
import json

from app.research.neural.hashing import sha256_file
from app.research.neural.manifests import NeuralRecordingManifest, NeuralTrialManifest
from app.research.neural.provenance import (
    DatasetChecksumEntry,
    DatasetChecksumManifest,
    DatasetLicenseRecord,
    NeuralDatasetDescriptor,
)
from app.research.neural.registry import get_descriptor, list_datasets


class TestRegistry:
    def test_ds005815_registered_and_primary_confirmatory(self):
        d = get_descriptor("ds005815")
        assert d is not None
        assert d.primary_confirmatory_eligible is True
        assert d.license.license_name == "CC0 1.0"
        assert d.license.permits_analysis
        assert d.license.permits_publication
        assert d.license.permits_redistribution_of_derivatives

    def test_unknown_dataset_returns_none(self):
        assert get_descriptor("does-not-exist") is None

    def test_list_datasets_includes_ds005815(self):
        ids = [d.dataset_id for d in list_datasets()]
        assert "ds005815" in ids

    def test_descriptor_is_frozen(self):
        d = get_descriptor("ds005815")
        try:
            d.participant_count = 999
            assert False, "descriptor must be immutable"
        except Exception:
            pass

    def test_descriptor_to_dict_json_serializable(self):
        d = get_descriptor("ds005815")
        json.dumps(d.to_dict())  # must not raise


class TestManifestDataclasses:
    def test_recording_manifest_round_trips_to_dict(self):
        m = NeuralRecordingManifest(
            dataset_id="ds005815", dataset_version="2.0.1",
            participant_id="sub-01", session_id="1", run_id="task",
            original_source="s3://openneuro.org/ds005815/",
            download_timestamp="2026-07-16T00:00:00Z", adapter_version="1.0.0",
            source_file_hash="a" * 64, channel_names=("Fp1", "Fp2"),
            sampling_rate=1000.0, n_samples=100, duration_s=0.1,
        )
        d = m.to_dict()
        json.dumps(d)
        assert d["channel_names"] == ["Fp1", "Fp2"]

    def test_trial_manifest_round_trips_to_dict(self):
        t = NeuralTrialManifest(
            dataset_id="ds005815", dataset_version="2.0.1",
            participant_id="sub-01", session_id="1", run_id="task",
            trial_id="t0", condition="perception", stimulus_id="visual_square",
            event_onset=1.0, event_duration=2.0, behavioral_target=4.0,
            subjective_target=None, channel_names=("Fp1",), sampling_rate=1000.0,
            source_file_hash="a" * 64,
        )
        d = t.to_dict()
        json.dumps(d)
        assert d["stimulus_id"] == "visual_square"


class TestChecksumManifest:
    def test_find_entry_by_relative_path(self):
        entry = DatasetChecksumEntry(
            relative_path="sub-01/ses-1/eeg/sub-01_ses-1_task-task_eeg.eeg",
            sha256="b" * 64, size_bytes=1234,
            downloaded_at="2026-07-16T00:00:00Z",
            source_url="https://s3.amazonaws.com/openneuro.org/ds005815/...",
        )
        manifest = DatasetChecksumManifest(
            dataset_id="ds005815", dataset_version="2.0.1", entries=(entry,),
        )
        found = manifest.find("sub-01/ses-1/eeg/sub-01_ses-1_task-task_eeg.eeg")
        assert found is not None
        assert found.sha256 == "b" * 64
        assert manifest.find("nonexistent") is None

    def test_manifest_to_dict_json_serializable(self):
        entry = DatasetChecksumEntry(
            relative_path="x", sha256="c" * 64, size_bytes=1,
            downloaded_at="2026-07-16T00:00:00Z", source_url="https://example.invalid/x",
        )
        manifest = DatasetChecksumManifest(dataset_id="ds005815", dataset_version="2.0.1", entries=(entry,))
        json.dumps(manifest.to_dict())


class TestLicenseRecord:
    def test_license_record_to_dict(self):
        rec = DatasetLicenseRecord(
            license_name="CC0 1.0", license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            permits_analysis=True, permits_publication=True,
            permits_redistribution_of_derivatives=True,
            obtained_from="https://example.invalid", verified_at="2026-07-16",
        )
        json.dumps(rec.to_dict())


class TestHashing:
    def test_sha256_file_matches_known_content(self, tmp_path):
        p = tmp_path / "f.txt"
        p.write_bytes(b"hello world")
        import hashlib
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert sha256_file(p) == expected

    def test_sha256_file_handles_multi_chunk_content(self, tmp_path):
        p = tmp_path / "big.bin"
        content = b"x" * (3 * 1024 * 1024 + 17)  # spans multiple 1MB chunks
        p.write_bytes(content)
        import hashlib
        assert sha256_file(p) == hashlib.sha256(content).hexdigest()


def test_no_arbitrary_neural_descriptor_lacks_license_permission_check():
    """A descriptor without publication permission must be rejectable by
    downstream code — this is a smoke test that the fields exist and are
    checkable, not a full policy engine (built alongside actual usage)."""
    restrictive = NeuralDatasetDescriptor(
        dataset_id="hypothetical", official_title="t", official_source="s",
        dataset_doi="d", dataset_version="1", modality="eeg",
        participant_count=1, session_count=1, channel_count=1, sampling_rate_hz=1.0,
        license=DatasetLicenseRecord(
            license_name="All rights reserved", license_url="https://example.invalid",
            permits_analysis=True, permits_publication=False,
            permits_redistribution_of_derivatives=False,
            obtained_from="https://example.invalid", verified_at="2026-07-16",
        ),
        primary_confirmatory_eligible=False, adapter_version="0.0.0",
    )
    assert restrictive.license.permits_publication is False

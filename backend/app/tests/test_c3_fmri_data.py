"""Tests for C3 fMRI data contracts and manifest integrity.

These tests run in CI without NSD data — they verify:
- Registry correctness
- Manifest dataclass construction
- Ingestion function signatures and error handling
- Environment variable requirements
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.research.fmri.ingestion import (
    get_imagery_run_types,
    get_nsd_data_root,
    get_stimulus_set_for_run,
    get_vision_run_types,
    validate_participant_data,
)
from app.research.fmri.manifests import (
    FMRIBetaFileManifest,
    FMRITrialManifest,
    NSDImageryManifest,
    NSDPerceptionManifest,
    ROIMaskManifest,
    StimulusEmbeddingManifest,
)
from app.research.fmri.registry import (
    ELIGIBLE_SUBJECTS,
    NSD_DESCRIPTOR,
    NSD_IMAGERY_DESCRIPTOR,
    get_descriptor,
    list_datasets,
)


class TestRegistry:
    def test_eligible_subjects(self):
        assert ELIGIBLE_SUBJECTS == ("subj01", "subj02", "subj05", "subj07")

    def test_nsd_descriptor_identity(self):
        assert NSD_DESCRIPTOR.dataset_id == "nsd"
        assert NSD_DESCRIPTOR.dataset_version == "1.0"
        assert NSD_DESCRIPTOR.modality == "7T_fMRI"
        assert NSD_DESCRIPTOR.beta_variant == "func1pt8mm/betas_fithrf"
        assert NSD_DESCRIPTOR.eligible_subjects == ("subj01", "subj02", "subj05", "subj07")
        assert NSD_DESCRIPTOR.total_subjects_scanned == 8
        assert NSD_DESCRIPTOR.role == "perception_decoder_training"

    def test_nsd_imagery_descriptor_identity(self):
        assert NSD_IMAGERY_DESCRIPTOR.dataset_id == "nsd_imagery"
        assert NSD_IMAGERY_DESCRIPTOR.dataset_version == "1.0"
        assert NSD_IMAGERY_DESCRIPTOR.modality == "7T_fMRI"
        assert NSD_IMAGERY_DESCRIPTOR.beta_variant == "func1pt8mm/nsdimagerybetas_fithrf"
        assert NSD_IMAGERY_DESCRIPTOR.role == "imagery_transfer_evaluation"

    def test_get_descriptor(self):
        assert get_descriptor("nsd") is NSD_DESCRIPTOR
        assert get_descriptor("nsd_imagery") is NSD_IMAGERY_DESCRIPTOR
        assert get_descriptor("nonexistent") is None

    def test_list_datasets(self):
        datasets = list_datasets()
        assert len(datasets) == 2
        ids = {d.dataset_id for d in datasets}
        assert ids == {"nsd", "nsd_imagery"}

    def test_nsd_license_permits_analysis(self):
        assert NSD_DESCRIPTOR.license.permits_analysis is True
        assert NSD_IMAGERY_DESCRIPTOR.license.permits_analysis is True

    def test_descriptors_are_frozen(self):
        with pytest.raises(Exception):
            NSD_DESCRIPTOR.dataset_id = "hacked"  # type: ignore[misc]


class TestManifests:
    def test_fmri_beta_file_manifest(self):
        m = FMRIBetaFileManifest(
            dataset_id="nsd_imagery",
            dataset_version="1.0",
            participant_id="subj01",
            beta_variant="func1pt8mm/nsdimagerybetas_fithrf",
            beta_space="func1pt8mm",
            file_path="/fake/path.hdf5",
            file_hash="abc123",
            file_size_bytes=1003740000,
            n_trials=288,
            n_voxels=200000,
            session_ids=("ses-imagery",),
        )
        d = m.to_dict()
        assert d["participant_id"] == "subj01"
        assert d["n_trials"] == 288
        assert isinstance(d["session_ids"], list)

    def test_roi_mask_manifest(self):
        m = ROIMaskManifest(
            dataset_id="nsd",
            participant_id="subj01",
            roi_id="nsdgeneral",
            roi_description="all visually responsive voxels",
            file_path="/fake/roi.nii.gz",
            file_hash="def456",
            n_voxels_in_mask=15000,
            space="func1pt8mm",
            label_values={"nsdgeneral": 1},
        )
        d = m.to_dict()
        assert d["n_voxels_in_mask"] == 15000

    def test_fmri_trial_manifest(self):
        m = FMRITrialManifest(
            dataset_id="nsd_imagery",
            dataset_version="1.0",
            participant_id="subj01",
            session_id="ses-imagery",
            run_id="imgB_1",
            trial_id="subj01_imgB1_trial003",
            state="imagery",
            stimulus_id="complex_scene_02",
            stimulus_set="complex",
            repeat_index=3,
            beta_variant="func1pt8mm/nsdimagerybetas_fithrf",
            beta_file_hash="abc123",
            voxel_mask_hash="def456",
            roi_id="nsdgeneral",
            ncsnr_policy="positive_voxels_only",
            stimulus_embedding_hash="ghi789",
            vividness_rating=1.0,
            cue_letter="B",
        )
        d = m.to_dict()
        assert d["state"] == "imagery"
        assert d["stimulus_set"] == "complex"

    def test_stimulus_embedding_manifest(self):
        m = StimulusEmbeddingManifest(
            model_name="openai/clip-vit-large-patch14",
            model_version="1.0",
            weights_source="huggingface",
            weights_hash="weights_sha256",
            embedding_dim=768,
            normalization="L2",
            preprocessing_hash="preproc_sha256",
            stimulus_ids=("stim_01", "stim_02"),
        )
        d = m.to_dict()
        assert d["embedding_dim"] == 768
        assert isinstance(d["stimulus_ids"], list)

    def test_nsd_perception_manifest(self):
        m = NSDPerceptionManifest(
            dataset_id="nsd",
            dataset_version="1.0",
            participant_id="subj01",
            n_sessions=40,
            n_total_trials=30000,
            n_unique_images=10000,
            n_shared1000_test_images=982,
            beta_variant="func1pt8mm/betas_fithrf",
            beta_space="func1pt8mm",
        )
        d = m.to_dict()
        assert d["n_sessions"] == 40

    def test_nsd_imagery_manifest(self):
        m = NSDImageryManifest(
            dataset_id="nsd_imagery",
            dataset_version="1.0",
            participant_id="subj01",
            n_imagery_trials=288,
            n_vision_trials=144,
            n_unique_stimuli=18,
            n_usable_stimuli=12,
            stimulus_sets={"simple": 6, "complex": 6, "conceptual": 6},
        )
        d = m.to_dict()
        assert d["n_usable_stimuli"] == 12


class TestIngestion:
    def test_run_types(self):
        imagery = get_imagery_run_types()
        assert len(imagery) == 6
        assert "imgA_1" in imagery
        assert "imgB_2" in imagery
        assert "imgC_1" in imagery

        vision = get_vision_run_types()
        assert len(vision) == 3
        assert "visA" in vision
        assert "visB" in vision
        assert "visC" in vision

    def test_stimulus_set_mapping(self):
        assert get_stimulus_set_for_run("imgA_1") == "simple"
        assert get_stimulus_set_for_run("imgB_2") == "complex"
        assert get_stimulus_set_for_run("imgC_1") == "conceptual"
        assert get_stimulus_set_for_run("visA") == "simple"
        assert get_stimulus_set_for_run("visB") == "complex"

    def test_stimulus_set_unknown_raises(self):
        with pytest.raises(ValueError):
            get_stimulus_set_for_run("unknown_run")

    def test_env_variable_required(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NSD_DATA_ROOT", None)
            with pytest.raises(EnvironmentError):
                get_nsd_data_root()

    def test_validate_participant_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NSD_DATA_ROOT", None)
            os.environ.pop("NSD_BETAS_ROOT", None)
            result = validate_participant_data("subj01")
            assert "error" in result

    def test_ineligible_participant_check(self):
        result = validate_participant_data("subj03")
        assert result["eligible"] is False


class TestProtocolArtifacts:
    """Verify JSON artifact integrity."""

    def test_c3_data_audit_valid(self):
        path = Path(__file__).resolve().parents[3] / "results" / "c3_data_audit.json"
        if not path.exists():
            pytest.skip("c3_data_audit.json not found in results/")
        data = json.loads(path.read_text())
        assert data["datasets"]["nsd_imagery"]["eligible_subjects"] == ["subj01", "subj02", "subj05", "subj07"]
        assert data["datasets"]["nsd_imagery"]["usable_stimuli_with_ground_truth"] == 12
        assert data["target_embedding"]["embedding_dim"] == 768

    def test_c3_protocol_decision_valid(self):
        path = Path(__file__).resolve().parents[3] / "results" / "c3_protocol_decision.json"
        if not path.exists():
            pytest.skip("c3_protocol_decision.json not found in results/")
        data = json.loads(path.read_text())
        assert data["primary_metric"] == "MRR_12_candidate_pool"
        assert data["n_participants"] == 4
        assert data["primary_roi"] == "nsdgeneral"
        assert "reconstruction_prohibition" in data

"""Provenance manifests for C3 fMRI ingestion.

Every fMRI trial and file must be traceable to its source, version,
and content hash. These dataclasses define the atomic provenance units.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FMRIBetaFileManifest:
    """Provenance for one ingested beta HDF5 file."""
    dataset_id: str
    dataset_version: str
    participant_id: str
    beta_variant: str
    beta_space: str
    file_path: str
    file_hash: str
    file_size_bytes: int
    n_trials: int
    n_voxels: int
    session_ids: tuple[str, ...] = ()
    downloaded_at: str = ""
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["session_ids"] = list(self.session_ids)
        return d


@dataclass(frozen=True)
class ROIMaskManifest:
    """Provenance for one ROI mask NIfTI file."""
    dataset_id: str
    participant_id: str
    roi_id: str
    roi_description: str
    file_path: str
    file_hash: str
    n_voxels_in_mask: int
    space: str
    label_values: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        return d


@dataclass(frozen=True)
class FMRITrialManifest:
    """Provenance for exactly one analyzable fMRI trial."""
    dataset_id: str
    dataset_version: str
    participant_id: str
    session_id: str
    run_id: str
    trial_id: str
    state: str  # "perception" or "imagery"
    stimulus_id: str
    stimulus_set: str  # "simple", "complex", "conceptual"
    repeat_index: int
    beta_variant: str
    beta_file_hash: str
    voxel_mask_hash: str
    roi_id: str
    ncsnr_policy: str
    stimulus_embedding_hash: str
    vividness_rating: float | None = None
    cue_letter: str = ""
    trial_onset_s: float = 0.0
    condition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class StimulusEmbeddingManifest:
    """Provenance for frozen stimulus target embeddings."""
    model_name: str
    model_version: str
    weights_source: str
    weights_hash: str
    embedding_dim: int
    normalization: str
    preprocessing_hash: str
    stimulus_ids: tuple[str, ...] = ()
    embeddings_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["stimulus_ids"] = list(self.stimulus_ids)
        return d


@dataclass(frozen=True)
class NSDPerceptionManifest:
    """Aggregate manifest for NSD perception data used in C3."""
    dataset_id: str
    dataset_version: str
    participant_id: str
    n_sessions: int
    n_total_trials: int
    n_unique_images: int
    n_shared1000_test_images: int
    beta_variant: str
    beta_space: str
    beta_file_hashes: tuple[str, ...] = ()
    roi_mask_hash: str = ""
    ncsnr_hash: str = ""
    train_image_ids: tuple[str, ...] = ()
    test_image_ids: tuple[str, ...] = ()
    split_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["beta_file_hashes"] = list(self.beta_file_hashes)
        d["train_image_ids"] = list(self.train_image_ids)
        d["test_image_ids"] = list(self.test_image_ids)
        return d


@dataclass(frozen=True)
class NSDImageryManifest:
    """Aggregate manifest for NSD-Imagery data used in C3."""
    dataset_id: str
    dataset_version: str
    participant_id: str
    n_imagery_trials: int
    n_vision_trials: int
    n_unique_stimuli: int
    n_usable_stimuli: int
    stimulus_sets: dict[str, int] = field(default_factory=dict)
    beta_variant: str = ""
    beta_space: str = ""
    beta_file_hash: str = ""
    roi_mask_hash: str = ""
    imagery_trial_manifests: tuple[FMRITrialManifest, ...] = ()
    vision_trial_manifests: tuple[FMRITrialManifest, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["imagery_trial_manifests"] = [t.to_dict() for t in self.imagery_trial_manifests]
        d["vision_trial_manifests"] = [t.to_dict() for t in self.vision_trial_manifests]
        return d

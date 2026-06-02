"""EEG Dataset Abstraction v6.1 — Base adapter interface."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateTask:
    task_name: str
    description: str
    positive_label: str
    negative_label: str
    label_source_fields: list = field(default_factory=lambda: ["event_code"])
    nuisance_metadata_fields: list = field(default_factory=lambda: ["run_id", "trial_index"])
    split_group_fields: list = field(default_factory=lambda: ["subject_id"])
    forbidden_model_feature_fields: list = field(default_factory=lambda:
                                                  ["event_code", "subject_id", "run_id", "trial_index"])
    split_strategy: str = "leave_one_subject_out"
    requires_stimulus_holdout: bool = False
    notes: str = ""


@dataclass
class AdapterManifest:
    dataset_name: str
    adapter_status: str  # "available", "data_unavailable", "dependency_missing"
    data_available: bool
    loader_backend: str  # "moabb", "mne", "unavailable"
    dependency_missing: list = field(default_factory=list)
    candidate_tasks: list = field(default_factory=list)
    recommended_first_task: Optional[str] = None
    install_suggestion: str = ""


class EEGDatasetAdapter:
    """Abstract base for EEG dataset adapters."""

    dataset_name: str = "unknown"

    def load_metadata(self):
        raise NotImplementedError

    def load_subjects(self):
        raise NotImplementedError

    def get_candidate_tasks(self) -> list[CandidateTask]:
        raise NotImplementedError

    def load_epochs(self, task_name: str, max_subjects: Optional[int] = None):
        raise NotImplementedError

    def export_manifest(self) -> AdapterManifest:
        raise NotImplementedError


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}

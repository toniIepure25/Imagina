"""Per-recording and per-trial provenance manifests for Scientific Gate C1.

Every dataset adapter must be able to produce a `NeuralRecordingManifest` per
ingested raw file and a `NeuralTrialManifest` per trial, exposing exactly the
fields required by the C1 commit plan. These are the atomic units later
persisted by the C0.2 evidence infrastructure (SQLite manifests + hashes),
not a replacement for it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NeuralRecordingManifest:
    """Provenance for one ingested raw recording file (one BIDS run)."""
    dataset_id: str
    dataset_version: str
    participant_id: str
    session_id: str
    run_id: str
    original_source: str
    download_timestamp: str
    adapter_version: str
    source_file_hash: str
    channel_names: tuple[str, ...]
    sampling_rate: float
    n_samples: int
    duration_s: float
    exclusions: tuple[str, ...] = ()
    metadata_repairs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["channel_names"] = list(self.channel_names)
        d["exclusions"] = list(self.exclusions)
        d["metadata_repairs"] = list(self.metadata_repairs)
        return d


@dataclass(frozen=True)
class NeuralTrialManifest:
    """Provenance and identity for exactly one analyzable trial-phase epoch.

    Perception and imagery phases of the same physical trial share the same
    `trial_id` but are separate `NeuralTrialManifest` rows (distinct
    `condition` and `event_onset`), since H1-H5 require them to be
    independently addressable while still traceable to one trial.
    """
    dataset_id: str
    dataset_version: str
    participant_id: str
    session_id: str
    run_id: str
    trial_id: str
    condition: str
    stimulus_id: str
    event_onset: float
    event_duration: float
    behavioral_target: float | None
    subjective_target: float | None
    channel_names: tuple[str, ...]
    sampling_rate: float
    source_file_hash: str

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["channel_names"] = list(self.channel_names)
        return d

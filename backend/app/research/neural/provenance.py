"""Immutable dataset-level provenance records for Scientific Gate C1.

These describe a dataset as a whole (identity, license, checksums) — distinct
from `manifests.py`, which describes individual ingested recordings and
trials. All dataclasses here are frozen: a dataset's identity, license terms,
and checksum ledger must not be mutated in place once created, only
superseded by a new record with a new `dataset_version`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DatasetLicenseRecord:
    """Data-use terms for a dataset, verified against the primary source."""
    license_name: str
    license_url: str
    permits_analysis: bool
    permits_publication: bool
    permits_redistribution_of_derivatives: bool
    obtained_from: str
    verified_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass(frozen=True)
class DatasetChecksumEntry:
    """A single verified file's checksum, independent of the source's own
    ETag/CRC — computed by this project on ingestion per its provenance
    convention (see Scientific Gate C0.2)."""
    relative_path: str
    sha256: str
    size_bytes: int
    downloaded_at: str
    source_url: str


@dataclass(frozen=True)
class DatasetChecksumManifest:
    """The full checksum ledger for one dataset_version's ingested files."""
    dataset_id: str
    dataset_version: str
    entries: tuple[DatasetChecksumEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "entries": [e.__dict__ for e in self.entries],
        }

    def find(self, relative_path: str) -> DatasetChecksumEntry | None:
        for e in self.entries:
            if e.relative_path == relative_path:
                return e
        return None


@dataclass(frozen=True)
class NeuralDatasetDescriptor:
    """Immutable identity and admissibility record for one neural dataset.

    Mirrors the fields verified in the Phase 0 audit
    (`results/c1_dataset_candidates.json`) but as importable, typed Python
    data rather than a JSON blob, so ingestion/adapter code can reference a
    single source of truth for "what is this dataset" without re-parsing
    JSON.
    """
    dataset_id: str
    official_title: str
    official_source: str
    dataset_doi: str
    dataset_version: str
    modality: str
    participant_count: int
    session_count: int
    channel_count: int
    sampling_rate_hz: float
    license: DatasetLicenseRecord
    primary_confirmatory_eligible: bool
    adapter_version: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if k != "license"}
        d["license"] = self.license.to_dict()
        return d

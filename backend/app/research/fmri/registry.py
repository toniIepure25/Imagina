"""Immutable dataset registry for Scientific Gate C3 (fMRI).

Registers NSD and NSD-Imagery with provenance-locked identity, license,
and admissibility records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FMRIDatasetLicense:
    license_name: str
    license_url: str
    permits_analysis: bool
    permits_publication: bool
    obtained_from: str
    verified_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class FMRIDatasetDescriptor:
    dataset_id: str
    official_title: str
    official_source: str
    dataset_doi: str
    dataset_version: str
    modality: str
    eligible_subjects: tuple[str, ...]
    total_subjects_scanned: int
    beta_variant: str
    voxel_resolution: str
    license: FMRIDatasetLicense
    role: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["eligible_subjects"] = list(self.eligible_subjects)
        d["license"] = self.license.to_dict()
        return d


NSD_LICENSE = FMRIDatasetLicense(
    license_name="Custom institutional agreement",
    license_url="https://cvnlab.slite.page/p/IB6BSeW_7o/Terms-and-Conditions",
    permits_analysis=True,
    permits_publication=True,
    obtained_from="https://naturalscenesdataset.org",
    verified_at="2026-07-24",
    notes="Requires institutional data use agreement. No redistribution of raw data.",
)

NSD_IMAGERY_LICENSE = FMRIDatasetLicense(
    license_name="CC-BY-NC-ND 4.0",
    license_url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
    permits_analysis=True,
    permits_publication=True,
    obtained_from="https://naturalscenesdataset.org",
    verified_at="2026-07-24",
    notes="NSD-Imagery released as CC-BY-NC-ND 4.0 per Kneeland et al. CVPR 2025.",
)

NSD_DESCRIPTOR = FMRIDatasetDescriptor(
    dataset_id="nsd",
    official_title="Natural Scenes Dataset",
    official_source="https://naturalscenesdataset.org",
    dataset_doi="doi:10.1038/s41593-021-00962-x",
    dataset_version="1.0",
    modality="7T_fMRI",
    eligible_subjects=("subj01", "subj02", "subj05", "subj07"),
    total_subjects_scanned=8,
    beta_variant="func1pt8mm/betas_fithrf",
    voxel_resolution="1.8mm_isotropic",
    license=NSD_LICENSE,
    role="perception_decoder_training",
    notes="Only subjects completing 40 sessions are eligible for C3.",
)

NSD_IMAGERY_DESCRIPTOR = FMRIDatasetDescriptor(
    dataset_id="nsd_imagery",
    official_title="NSD-Imagery: A benchmark dataset for extending fMRI vision decoding methods to mental imagery",
    official_source="https://naturalscenesdataset.org",
    dataset_doi="doi:10.48550/arXiv.2506.06898",
    dataset_version="1.0",
    modality="7T_fMRI",
    eligible_subjects=("subj01", "subj02", "subj05", "subj07"),
    total_subjects_scanned=8,
    beta_variant="func1pt8mm/nsdimagerybetas_fithrf",
    voxel_resolution="1.8mm_isotropic",
    license=NSD_IMAGERY_LICENSE,
    role="imagery_transfer_evaluation",
    notes="18 unique stimuli, 576 trials/subject. Kneeland et al. CVPR 2025.",
)


_REGISTRY: dict[str, FMRIDatasetDescriptor] = {
    "nsd": NSD_DESCRIPTOR,
    "nsd_imagery": NSD_IMAGERY_DESCRIPTOR,
}


def get_descriptor(dataset_id: str) -> FMRIDatasetDescriptor | None:
    return _REGISTRY.get(dataset_id)


def list_datasets() -> list[FMRIDatasetDescriptor]:
    return list(_REGISTRY.values())


ELIGIBLE_SUBJECTS = ("subj01", "subj02", "subj05", "subj07")

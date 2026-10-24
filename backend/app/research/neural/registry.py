"""Immutable neural dataset registry for Scientific Gate C1.

Populated from the primary-source-verified Phase 0 audit
(`results/c1_dataset_candidates.json`, `docs/research/C1_DATASET_CANDIDATES.md`).
Only datasets actually given a concrete ingestion adapter are registered here
in full; the registry is the single place code asks "what dataset is this
and can I trust it," rather than re-deriving admissibility from the JSON
audit file at runtime.
"""
from __future__ import annotations

from app.research.neural.provenance import DatasetLicenseRecord, NeuralDatasetDescriptor

YOTO_LICENSE = DatasetLicenseRecord(
    license_name="CC0 1.0",
    license_url="https://creativecommons.org/publicdomain/zero/1.0/",
    permits_analysis=True,
    permits_publication=True,
    permits_redistribution_of_derivatives=True,
    obtained_from="https://s3.amazonaws.com/openneuro.org/ds005815/dataset_description.json",
    verified_at="2026-07-16",
    notes=(
        "Relicensed from CC-BY-4.0 to CC0 on 2025-01-12 per the dataset's own "
        "CHANGES file, verified directly against the S3-mirrored BIDS files "
        "(not the OpenNeuro web UI, which requires a JS-rendering client)."
    ),
)

YOTO_DESCRIPTOR = NeuralDatasetDescriptor(
    dataset_id="ds005815",
    official_title="A Human EEG Dataset for Multisensory Perception and Mental Imagery (YOTO)",
    official_source="https://openneuro.org/datasets/ds005815",
    dataset_doi="doi:10.18112/openneuro.ds005815.v2.0.1",
    dataset_version="2.0.1",
    modality="eeg-visual-auditory-multimodal-perception-imagery",
    participant_count=20,
    session_count=2,
    channel_count=30,
    sampling_rate_hz=1000.0,
    license=YOTO_LICENSE,
    primary_confirmatory_eligible=True,
    adapter_version="1.0.0",
    notes=(
        "Primary confirmatory dataset for C1 (docs/research/C1_PROTOCOL.md). "
        "Trigger-code semantics decoded from the dataset authors' own "
        "analysis code (see trigger_codebook.py), not guessed."
    ),
)

_REGISTRY: dict[str, NeuralDatasetDescriptor] = {
    "ds005815": YOTO_DESCRIPTOR,
}


def get_descriptor(dataset_id: str) -> NeuralDatasetDescriptor | None:
    return _REGISTRY.get(dataset_id)


def list_datasets() -> list[NeuralDatasetDescriptor]:
    return list(_REGISTRY.values())

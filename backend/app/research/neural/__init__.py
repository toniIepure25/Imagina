"""Scientific Gate C1 — neural dataset registry, provenance, and ingestion.

Deliberately kept separate from `backend/app/datasets/` (the older, thinner
dataset-import system used by the synthetic/fixture-oriented real-EEG-import
CLI flow) and from the empty `backend/app/research/datasets/` /
`backend/app/research/eeg_validation/` stubs left over from an earlier,
partially-executed repository restructure (see `docs/RESTRUCTURE_AUDIT.md`).
This package is the single source of truth for C1 neural-behavioral
alignment work: immutable dataset descriptors, per-recording and per-trial
provenance manifests, checksum/license records, and dataset adapters.
"""

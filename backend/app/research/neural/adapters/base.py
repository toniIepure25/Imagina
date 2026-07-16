"""Abstract dataset adapter contract for Scientific Gate C1.

Every dataset adapter must be able to ingest one recording (one BIDS run)
and produce a `NeuralRecordingManifest` plus the `NeuralTrialManifest` rows
it contains, using only the fields listed in the C1 commit plan. Adapters
must never fabricate a condition, stimulus identity, or behavioral target —
an unresolvable trigger/event must be excluded and recorded in
`NeuralRecordingManifest.exclusions`, not silently defaulted.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.research.neural.manifests import NeuralRecordingManifest, NeuralTrialManifest


class NeuralDatasetAdapter(ABC):
    dataset_id: str
    dataset_version: str
    adapter_version: str

    @abstractmethod
    def ingest_recording(
        self, participant_id: str, session_id: str, run_id: str,
    ) -> tuple[NeuralRecordingManifest, list[NeuralTrialManifest]]:
        """Ingest one raw recording and return its manifest plus every
        trial-phase manifest it contains. Must be a pure function of the
        on-disk raw files for the given participant/session/run — no
        network access, no randomness."""
        raise NotImplementedError

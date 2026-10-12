from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Callable

from app.multimodal.acquisition.synthetic import SYNTHETIC_REALTIME
from app.multimodal.schemas import Modality, SourceKind


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    modality: Modality
    source_kind: SourceKind
    support_level: str
    realtime: bool
    formats: tuple[str, ...] = ()
    requires_package: str | None = None
    note: str = ""
    factory: Callable | None = None

    def available(self) -> bool:
        return self.requires_package is None or importlib.util.find_spec(self.requires_package) is not None

    def describe(self) -> dict:
        return {
            "provider_id": self.provider_id, "modality": self.modality.value, "source_kind": self.source_kind.value,
            "support_level": self.support_level, "realtime": self.realtime, "formats": list(self.formats),
            "requires_package": self.requires_package, "available": self.available(), "note": self.note,
        }


def _build() -> list[ProviderDescriptor]:
    d: list[ProviderDescriptor] = []
    for modality, cls in SYNTHETIC_REALTIME.items():
        d.append(ProviderDescriptor(f"synthetic.{modality.value}", modality, SourceKind.SYNTHETIC, "IMPLEMENTED",
                                    True, factory=cls, note="Deterministic synthetic engineering signal."))
    d += [
        ProviderDescriptor("synthetic.meg", Modality.MEG, SourceKind.SYNTHETIC, "IMPLEMENTED", False, ("FIF",),
                           note="Offline synthetic FIF fixture generator."),
        ProviderDescriptor("synthetic.fmri", Modality.FMRI, SourceKind.SYNTHETIC, "IMPLEMENTED", False,
                           ("BIDS", "NIfTI"), note="Offline synthetic BIDS fixture generator."),
        ProviderDescriptor("replay.eeg", Modality.EEG, SourceKind.REPLAY, "IMPLEMENTED", True,
                           ("EDF", "FIF", "CSV", "JSONL", "IMAGINA-HDF5"), "mne"),
        ProviderDescriptor("replay.ecg", Modality.ECG, SourceKind.REPLAY, "IMPLEMENTED", True,
                           ("EDF", "CSV", "JSONL", "IMAGINA-HDF5"), "mne"),
        ProviderDescriptor("replay.eda", Modality.EDA, SourceKind.REPLAY, "IMPLEMENTED", True,
                           ("EDF", "CSV", "JSONL", "IMAGINA-HDF5"), "mne"),
        ProviderDescriptor("replay.respiration", Modality.RESPIRATION, SourceKind.REPLAY, "IMPLEMENTED", True,
                           ("EDF", "CSV", "JSONL", "IMAGINA-HDF5"), "mne"),
        ProviderDescriptor("replay.fnirs", Modality.FNIRS, SourceKind.REPLAY, "IMPLEMENTED", True,
                           ("SNIRF", "IMAGINA-HDF5"), "h5py"),
        ProviderDescriptor("replay.meg", Modality.MEG, SourceKind.REPLAY, "IMPLEMENTED", False, ("FIF",), "mne",
                           note="Offline research modality."),
        ProviderDescriptor("replay.fmri", Modality.FMRI, SourceKind.REPLAY, "IMPLEMENTED", False, ("BIDS", "NIfTI"),
                           "nibabel", note="Offline research modality; not scanner neurofeedback."),
    ]
    for modality in (Modality.EEG, Modality.ECG, Modality.EDA, Modality.RESPIRATION, Modality.FNIRS):
        d.append(ProviderDescriptor(f"lsl.{modality.value}", modality, SourceKind.REAL_SENSOR, "INTERFACE_ONLY", True,
                                    requires_package="pylsl",
                                    note="Generic LSL inlet; no specific device validated."))
    d += [
        ProviderDescriptor("brainflow.board", Modality.EEG, SourceKind.REAL_SENSOR, "INTERFACE_ONLY", True,
                           requires_package="brainflow", note="BrainFlow BoardShim passthrough; not validated."),
        ProviderDescriptor("ads1299.diy", Modality.EEG, SourceKind.REAL_SENSOR, "HARDWARE_REQUIRED", True,
                           note="Transport-independent frame decoder; bench-test only, no human connection."),
        ProviderDescriptor("realtime.meg", Modality.MEG, SourceKind.REAL_SENSOR, "NOT_IMPLEMENTED", False,
                           note="No validated real-time MEG source available."),
        ProviderDescriptor("realtime.fmri", Modality.FMRI, SourceKind.REAL_SENSOR, "NOT_IMPLEMENTED", False,
                           note="Real-time scanner export not available; fMRI is offline-only here."),
    ]
    return d


REGISTRY: list[ProviderDescriptor] = _build()


def list_descriptors(modality: Modality | None = None) -> list[ProviderDescriptor]:
    return [d for d in REGISTRY if modality is None or d.modality == modality]


def get_descriptor(provider_id: str) -> ProviderDescriptor | None:
    return next((d for d in REGISTRY if d.provider_id == provider_id), None)


def create_synthetic(modality: Modality, **kwargs):
    if modality not in SYNTHETIC_REALTIME:
        raise ValueError(f"{modality.value} has no real-time synthetic stream; use the offline fixture generator")
    return SYNTHETIC_REALTIME[modality](**kwargs)

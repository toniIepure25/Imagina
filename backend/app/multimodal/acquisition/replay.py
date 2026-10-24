"""File readers and replay providers. Replayed data keeps the provenance (path + SHA-256) of its source file."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.multimodal.acquisition.base import ArrayStreamProvider, FaultPlan
from app.multimodal.schemas import Capabilities, ChannelSpec, Modality, Provenance, SourceKind, StreamInfo

_MNE_UNIT = {107: "V", 112: "T", 201: "T/m"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class LoadedRecording:
    modality: Modality
    rate_hz: float
    channels: list[ChannelSpec]
    data: np.ndarray
    path: Path
    events: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def stream_info(self, provider_id: str, realtime_capable: bool = True) -> StreamInfo:
        return StreamInfo(
            stream_id=f"{provider_id}:{self.path.name}",
            modality=self.modality,
            nominal_rate_hz=self.rate_hz,
            channels=self.channels,
            realtime_capable=realtime_capable,
            provenance=Provenance(
                source_kind=SourceKind.REPLAY, provider_id=provider_id, provider_version="1.0",
                file_path=str(self.path), file_sha256=sha256_file(self.path),
                notes=str(self.metadata.get("origin_note", "")),
            ),
            metadata={"sync_method": "file_timebase", **self.metadata},
        )


def edf_header_dims(path: Path) -> tuple[list[str], list[str], str]:
    with open(path, "rb") as fh:
        head = fh.read(256)
        ns = int(head[252:256].decode("ascii").strip())
        sig = fh.read(256 * ns)
    labels = [sig[i * 16:(i + 1) * 16].decode("ascii").strip() for i in range(ns)]
    off = ns * (16 + 80)
    dims = [sig[off + i * 8: off + (i + 1) * 8].decode("ascii").strip() for i in range(ns)]
    return labels, dims, head[8:88].decode("ascii", "replace").strip()


def read_edf(path: Path, modality: Modality) -> LoadedRecording:
    import mne

    labels, dims, patient = edf_header_dims(path)
    raw = mne.io.read_raw_edf(path, preload=True, verbose="error")
    to_declared = {"V": 1.0, "mV": 1e3, "uV": 1e6}
    scales = np.array([to_declared.get(d, 1.0) for d in dims])
    chans = [ChannelSpec(name=n, unit=d, kind=modality.value) for n, d in zip(raw.ch_names, dims)]
    note = "synthetic fixture" if "IMAGINA-SYNTHETIC" in patient else ""
    return LoadedRecording(modality, float(raw.info["sfreq"]), chans, raw.get_data().T * scales, path,
                           metadata={"format": "EDF", "origin_note": note})


def read_snirf(path: Path) -> LoadedRecording:
    import mne

    raw = mne.io.read_raw_snirf(path, preload=True, verbose="error")
    chans = []
    for ch in raw.info["chs"]:
        loc = ch["loc"]
        chans.append(ChannelSpec(
            name=ch["ch_name"], unit="a.u.", kind="fnirs_cw_amplitude", wavelength_nm=float(loc[9]),
            source_position_m=tuple(float(x) for x in loc[3:6]),
            detector_position_m=tuple(float(x) for x in loc[6:9]),
        ))
    return LoadedRecording(Modality.FNIRS, float(raw.info["sfreq"]), chans, raw.get_data().T, path,
                           metadata={"format": "SNIRF", "measurement": "cw_amplitude"})


def read_fif(path: Path) -> LoadedRecording:
    import mne

    raw = mne.io.read_raw_fif(path, preload=True, verbose="error")
    picks = mne.pick_types(raw.info, meg=True, eeg=True, exclude=[])
    types = set(raw.get_channel_types(picks=picks))
    modality = Modality.MEG if types & {"mag", "grad"} else Modality.EEG
    chans, scales = [], []
    for p in picks:
        ch = raw.info["chs"][p]
        unit = _MNE_UNIT.get(int(ch["unit"]), "T")
        if modality == Modality.EEG:
            unit, s = "uV", 1e6
        else:
            s = 1.0
        chans.append(ChannelSpec(name=ch["ch_name"], unit=unit, kind=raw.get_channel_types(picks=[p])[0]))
        scales.append(s)
    events = []
    stim = mne.pick_types(raw.info, meg=False, stim=True)
    if len(stim):
        for onset, _, code in mne.find_events(raw, verbose="error"):
            events.append({"sample": int(onset - raw.first_samp), "code": int(code)})
    data = raw.get_data(picks=picks).T * np.array(scales)
    return LoadedRecording(modality, float(raw.info["sfreq"]), chans, data, path, events=events,
                           metadata={"format": "FIF", "description": raw.info.get("description") or ""})


def read_tabular(path: Path) -> LoadedRecording:
    """CSV or JSONL with a JSON sidecar (``<file>.json``) declaring modality, rate_hz and channel units."""
    sidecar = json.loads(Path(str(path) + ".json").read_text())
    for key in ("modality", "rate_hz", "channels"):
        if key not in sidecar:
            raise ValueError(f"sidecar missing required key '{key}'")
    modality = Modality(sidecar["modality"])
    chans = [ChannelSpec(**c) for c in sidecar["channels"]]
    names = [c.name for c in chans]
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        with open(path, newline="") as fh:
            rows = list(csv.DictReader(fh))
    missing = [n for n in names if rows and n not in rows[0]]
    if missing:
        raise ValueError(f"columns missing for declared channels: {missing}")
    data = np.array([[float(r[n]) for n in names] for r in rows])
    return LoadedRecording(modality, float(sidecar["rate_hz"]), chans, data, path,
                           metadata={"format": path.suffix.lstrip(".").upper(), **sidecar.get("metadata", {})})


def load_recording(path: Path, modality: Modality | None = None) -> LoadedRecording:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".edf":
        if modality is None:
            raise ValueError("EDF requires the modality to be declared")
        return read_edf(path, modality)
    if suffix == ".snirf":
        return read_snirf(path)
    if suffix == ".fif":
        return read_fif(path)
    if suffix in {".csv", ".jsonl"}:
        return read_tabular(path)
    if suffix in {".h5", ".hdf5"}:
        from app.multimodal.storage import read_stream_recording
        return read_stream_recording(path)
    raise ValueError(f"unsupported recording format: {suffix}")


class FileReplayProvider(ArrayStreamProvider):
    source_kind = SourceKind.REPLAY

    def __init__(self, path: Path, modality: Modality | None = None, faults: FaultPlan | None = None) -> None:
        super().__init__(faults=faults)
        self.path = Path(path)
        self._declared_modality = modality
        self.recording: LoadedRecording | None = None
        self.modality = modality or Modality.EEG
        self.provider_id = f"replay.{self.path.suffix.lstrip('.')}"

    def capabilities(self) -> Capabilities:
        ok = self.path.exists()
        return Capabilities(
            provider_id=self.provider_id, modality=self.modality, source_kind=self.source_kind, available=ok,
            reason="" if ok else f"file not found: {self.path}", realtime=False, support_level="IMPLEMENTED",
        )

    def _materialize(self):
        rec = load_recording(self.path, self._declared_modality)
        self.recording = rec
        self.modality = rec.modality
        self.provider_id = f"replay.{rec.modality.value}"
        realtime = rec.modality not in {Modality.MEG, Modality.FMRI}
        return rec.stream_info(self.provider_id, realtime_capable=realtime), rec.data

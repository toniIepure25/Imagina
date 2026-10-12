from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.multimodal import SCHEMA_VERSION


class Modality(str, Enum):
    EEG = "eeg"
    ECG = "ecg"
    EDA = "eda"
    RESPIRATION = "respiration"
    FNIRS = "fnirs"
    MEG = "meg"
    FMRI = "fmri"


HRV_DERIVED_FROM = Modality.ECG

OFFLINE_ONLY_MODALITIES = frozenset({Modality.MEG, Modality.FMRI})


class SourceKind(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    REPLAY = "REPLAY"
    REAL_SENSOR = "REAL_SENSOR"


class EvidenceClass(str, Enum):
    DIRECT_MEASUREMENT = "DIRECT_MEASUREMENT"
    DERIVED_METRIC = "DERIVED_METRIC"
    VALIDATED_ESTIMATE = "VALIDATED_ESTIMATE"
    EXPERIMENTAL_PROXY = "EXPERIMENTAL_PROXY"
    SUBJECTIVE_REPORT = "SUBJECTIVE_REPORT"


ALLOWED_UNITS: dict[Modality, frozenset[str]] = {
    Modality.EEG: frozenset({"uV", "V"}),
    Modality.ECG: frozenset({"mV", "uV", "V"}),
    Modality.EDA: frozenset({"uS"}),
    Modality.RESPIRATION: frozenset({"a.u.", "mV", "V", "L"}),
    Modality.FNIRS: frozenset({"a.u.", "V", "OD", "M", "uM"}),
    Modality.MEG: frozenset({"T", "T/m", "fT"}),
    Modality.FMRI: frozenset({"a.u.", "BOLD"}),
}

NOMINAL_RATE_RANGE_HZ: dict[Modality, tuple[float, float]] = {
    Modality.EEG: (100.0, 4000.0),
    Modality.ECG: (100.0, 4000.0),
    Modality.EDA: (2.0, 1000.0),
    Modality.RESPIRATION: (5.0, 1000.0),
    Modality.FNIRS: (1.0, 100.0),
    Modality.MEG: (100.0, 12000.0),
    Modality.FMRI: (0.05, 5.0),
}


class ChannelSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    unit: str
    kind: str = "signal"
    wavelength_nm: float | None = None
    source_position_m: tuple[float, float, float] | None = None
    detector_position_m: tuple[float, float, float] | None = None


class Provenance(BaseModel):
    source_kind: SourceKind
    provider_id: str
    provider_version: str
    generator_seed: int | None = None
    file_path: str | None = None
    file_sha256: str | None = None
    device_model: str | None = None
    device_serial_hash: str | None = None
    notes: str = ""
    schema_version: str = SCHEMA_VERSION


class StreamInfo(BaseModel):
    stream_id: str
    modality: Modality
    nominal_rate_hz: float = Field(gt=0)
    channels: list[ChannelSpec]
    provenance: Provenance
    realtime_capable: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self) -> StreamInfo:
        lo, hi = NOMINAL_RATE_RANGE_HZ[self.modality]
        if not lo <= self.nominal_rate_hz <= hi:
            raise ValueError(f"{self.modality.value} rate {self.nominal_rate_hz} Hz outside [{lo}, {hi}]")
        if not self.channels:
            raise ValueError("stream must declare at least one channel")
        names = [c.name for c in self.channels]
        if len(set(names)) != len(names):
            raise ValueError("duplicate channel names")
        allowed = ALLOWED_UNITS[self.modality]
        bad = [c.name for c in self.channels if c.unit not in allowed]
        if bad:
            raise ValueError(f"channels {bad} have units not allowed for {self.modality.value}: {sorted(allowed)}")
        if self.modality in OFFLINE_ONLY_MODALITIES and self.realtime_capable:
            if self.provenance.source_kind != SourceKind.REAL_SENSOR:
                raise ValueError(f"{self.modality.value} is an offline research modality")
        return self

    @property
    def channel_names(self) -> list[str]:
        return [c.name for c in self.channels]

    @property
    def source_kind(self) -> SourceKind:
        return self.provenance.source_kind


class Capabilities(BaseModel):
    provider_id: str
    modality: Modality
    source_kind: SourceKind
    available: bool
    reason: str = ""
    realtime: bool
    supported_rates_hz: list[float] = Field(default_factory=list)
    max_channels: int | None = None
    requires_package: str | None = None
    support_level: str


class SampleChunk(BaseModel):
    """Block of samples. ``data`` is (n_samples, n_channels)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stream_id: str
    data: np.ndarray
    device_timestamps: np.ndarray
    local_timestamps: np.ndarray
    sample_indices: np.ndarray
    dropped_before: int = Field(default=0, ge=0)

    @field_validator("data", "device_timestamps", "local_timestamps", mode="before")
    @classmethod
    def _as_array(cls, v: Any) -> np.ndarray:
        return np.asarray(v, dtype=float)

    @field_validator("sample_indices", mode="before")
    @classmethod
    def _as_index(cls, v: Any) -> np.ndarray:
        return np.asarray(v, dtype=np.int64)

    @model_validator(mode="after")
    def _shapes(self) -> SampleChunk:
        if self.data.ndim != 2:
            raise ValueError("data must be 2-D (samples, channels)")
        n = self.data.shape[0]
        for arr in (self.device_timestamps, self.local_timestamps, self.sample_indices):
            if arr.shape != (n,):
                raise ValueError("timestamp and index arrays must match sample count")
        if n > 1 and np.any(np.diff(self.sample_indices) <= 0):
            raise ValueError("sample indices must be strictly increasing")
        if n > 1 and np.any(np.diff(self.local_timestamps) < 0):
            raise ValueError("local timestamps must be monotonic")
        return self

    @property
    def n_samples(self) -> int:
        return int(self.data.shape[0])

    @property
    def first_sample_index(self) -> int:
        return int(self.sample_indices[0]) if self.n_samples else -1


class QualityReport(BaseModel):
    stream_id: str
    modality: Modality
    score: float = Field(ge=0, le=1)
    usable: bool
    flags: list[str] = Field(default_factory=list)
    per_channel: dict[str, float] = Field(default_factory=dict)


class Marker(BaseModel):
    label: str
    local_time: float
    duration_s: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, default=_json_default, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _json_default(o: Any) -> Any:
    if isinstance(o, np.ndarray):
        return np.round(o, 10).tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, BaseModel):
        return o.model_dump(mode="json")
    raise TypeError(f"not serializable: {type(o)}")

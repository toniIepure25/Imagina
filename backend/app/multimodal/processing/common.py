from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field
from scipy import signal as sps

from app.multimodal.schemas import EvidenceClass, Modality, SourceKind


class Feature(BaseModel):
    name: str
    value: float | None
    unit: str
    evidence_class: EvidenceClass = EvidenceClass.DERIVED_METRIC
    confidence: float = Field(default=1.0, ge=0, le=1)
    method: str = ""
    reason: str = ""

    @property
    def valid(self) -> bool:
        return self.value is not None and np.isfinite(self.value)


class FeatureSet(BaseModel):
    modality: Modality
    stream_id: str
    source_kind: SourceKind
    t_start: float
    t_end: float
    quality: float = Field(ge=0, le=1)
    flags: list[str] = Field(default_factory=list)
    features: dict[str, Feature] = Field(default_factory=dict)
    pipeline_version: str = "1.0"

    def add(self, f: Feature) -> None:
        self.features[f.name] = f

    def value(self, name: str) -> float | None:
        f = self.features.get(name)
        return f.value if f is not None and f.valid else None

    def vector(self, names: list[str]) -> np.ndarray:
        return np.array([np.nan if self.value(n) is None else self.value(n) for n in names], dtype=float)


def withheld(name: str, unit: str, reason: str, method: str = "") -> Feature:
    return Feature(name=name, value=None, unit=unit, confidence=0.0, reason=reason, method=method)


def butter_filter(x: np.ndarray, fs: float, low: float | None, high: float | None, order: int = 2) -> np.ndarray:
    nyq = fs / 2.0
    if low is not None and high is not None:
        sos = sps.butter(order, [low / nyq, min(high / nyq, 0.99)], btype="band", output="sos")
    elif low is not None:
        sos = sps.butter(order, low / nyq, btype="high", output="sos")
    elif high is not None:
        sos = sps.butter(order, min(high / nyq, 0.99), btype="low", output="sos")
    else:
        return x
    padlen = min(x.shape[0] - 1, 3 * (2 * len(sos) + 1) * 10)
    return sps.sosfiltfilt(sos, x, axis=0, padlen=max(padlen, 0))


def flatline_fraction(x: np.ndarray, fs: float, win_s: float = 1.0, tol: float = 1e-9) -> float:
    w = max(int(win_s * fs), 2)
    n = x.shape[0] // w
    if n == 0:
        return 0.0
    segs = x[: n * w].reshape(n, w)
    return float(np.mean(np.ptp(segs, axis=1) <= tol))

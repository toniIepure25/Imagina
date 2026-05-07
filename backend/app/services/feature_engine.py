"""Normalizes and combines simulated features with self-report data."""

from app.schemas.features import FeatureVector


class FeatureEngine:
    """V1: pass-through since SignalSimulator already produces normalised features.

    Exists as an explicit pipeline step so V2 can plug in real preprocessing
    (MNE bandpower extraction, artifact rejection, etc.) without changing
    downstream consumers.
    """

    def process(self, raw: FeatureVector, self_report: dict | None = None) -> FeatureVector:
        return raw

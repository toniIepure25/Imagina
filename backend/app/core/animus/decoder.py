"""ANIMUS neural-content-decoder contract (the future-pluggable boundary).

Defines the interface a future *validated* neural decoder will implement, and a SYNTHETIC reference
implementation used in ANIMUS-P1. ANIMUS-P1 fabricates no real decoder and makes no neural-content claim:
the synthetic decoder inverts a known synthetic forward operator on a simulated measurement. The C3XAT/
C3XRP reliability evidence is measurement evidence only and is NEVER turned into content information here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from app.core.animus.claims import L0_SIMULATED


@dataclass
class NeuralDecodedBelief:
    """Output of a NeuralContentDecoder: a content estimate with uncertainty + provenance."""
    latent_estimate: list[float]
    uncertainty: list[float]
    quality: float
    valid: bool
    validity_flags: dict
    provenance: dict
    decoder_version: str
    training_dataset: str
    roi: str
    measurement_unit: str
    claim_level: str = L0_SIMULATED

    def to_dict(self) -> dict:
        return {"latent_estimate": [round(float(v), 6) for v in self.latent_estimate],
                "uncertainty": [round(float(v), 6) for v in self.uncertainty],
                "quality": round(float(self.quality), 6), "valid": bool(self.valid),
                "validity_flags": self.validity_flags, "provenance": self.provenance,
                "decoder_version": self.decoder_version, "training_dataset": self.training_dataset,
                "roi": self.roi, "measurement_unit": self.measurement_unit,
                "claim_level": self.claim_level}


@dataclass
class CalibrationContext:
    """What a decoder needs to map a raw measurement to a content estimate."""
    forward_operator: np.ndarray        # A: latent -> measurement (synthetic)
    measurement_noise: float
    roi: str = "synthetic-roi"
    unit: str = "synthetic-au"


class NeuralContentDecoder(ABC):
    """The stable interface the future real decoder must implement."""

    @abstractmethod
    def decode(self, neural_observation: np.ndarray, calibration_context: CalibrationContext,
               previous_belief) -> NeuralDecodedBelief:
        ...


class SyntheticNeuralDecoder(NeuralContentDecoder):
    """Reference decoder: least-squares inversion of the synthetic forward operator. NOT a real decoder;
    carries no validated-neural claim (stays L0)."""

    version = "synthetic-decoder-v1"

    def decode(self, neural_observation, calibration_context, previous_belief) -> NeuralDecodedBelief:
        A = np.asarray(calibration_context.forward_operator, float)
        y = np.asarray(neural_observation, float)
        est, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = float(np.linalg.norm(A @ est - y) / (np.linalg.norm(y) + 1e-9))
        quality = float(np.clip(1.0 - resid, 0.0, 1.0))
        unc = np.full(est.shape, float(calibration_context.measurement_noise ** 2 + resid))
        return NeuralDecodedBelief(
            latent_estimate=list(est), uncertainty=list(unc), quality=quality,
            valid=quality > 0.05, validity_flags={"residual_ok": resid < 5.0, "synthetic": True},
            provenance={"decoder": self.version, "synthetic": True, "not_validated": True},
            decoder_version=self.version, training_dataset="SYNTHETIC (none)",
            roi=calibration_context.roi, measurement_unit=calibration_context.unit,
            claim_level=L0_SIMULATED)


def make_forward_operator(dim: int, seed: int) -> np.ndarray:
    """A fixed, well-conditioned synthetic measurement operator A (dim x dim) for a calibration seed."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((dim, dim))
    q, _ = np.linalg.qr(a)              # orthonormal -> perfectly conditioned, invertible
    return q

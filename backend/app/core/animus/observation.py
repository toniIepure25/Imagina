"""ANIMUS observation providers.

An ``ObservationProvider`` turns a request (given the current candidate/probe context and the hidden twin)
into a typed ``ObservationEnvelope``. Source modes are explicit and never silently substituted: if a mode
is unavailable the provider raises rather than falling back. The future real neural decoder plugs in behind
``FutureNeuralDecoderProvider`` without touching the loop.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from app.core.animus.claims import (
    L0_SIMULATED,
    L1_BEHAVIORAL_ASSISTED,
    L3_NEURAL_CONTENT_INFORMED_VALIDATED,
)
from app.core.animus.decoder import CalibrationContext, SyntheticNeuralDecoder, make_forward_operator
from app.core.animus.models import (
    SOURCE_BEHAVIORAL,
    SOURCE_REPLAY,
    SOURCE_SIMULATED_NEURAL,
    SOURCE_VALIDATED_NEURAL_FUTURE,
    ObservationEnvelope,
)
from app.core.animus.synthetic_imaginer import SyntheticImaginer
from app.core.time import utcnow


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider's source mode cannot produce a valid observation (fail-closed)."""


class ObservationProvider(ABC):
    source_type: str
    claim_level: str

    @abstractmethod
    def observe(self, context: dict) -> ObservationEnvelope:
        ...


class SyntheticNeuralObservationProvider(ObservationProvider):
    """Simulated neural measurement -> synthetic decoder -> visual embedding observation. Stays L0."""
    source_type = SOURCE_SIMULATED_NEURAL
    claim_level = L0_SIMULATED

    def __init__(self, imaginer: SyntheticImaginer, calibration_seed: int, dim: int):
        self.imaginer = imaginer
        self.decoder = SyntheticNeuralDecoder()
        self.calib = CalibrationContext(
            forward_operator=make_forward_operator(dim, calibration_seed),
            measurement_noise=imaginer.params.neural_noise)

    def observe(self, context: dict) -> ObservationEnvelope:
        raw = self.imaginer.raw_neural_measurement(self.calib.forward_operator)
        decoded = self.decoder.decode(raw, self.calib, context.get("previous_belief"))
        if not decoded.valid:
            raise ProviderUnavailableError("synthetic neural decode invalid")
        sem, sem_var = self.imaginer.semantic_measurement()
        return ObservationEnvelope(
            source_type=self.source_type,
            representation={"visual": decoded.latent_estimate, "semantic": list(sem)},
            uncertainty={"visual": float(np.mean(decoded.uncertainty)), "semantic": sem_var},
            signal_quality=decoded.quality,
            measurement_id=context.get("measurement_id", "sim-neural"),
            timestamp=utcnow().isoformat(),
            provenance={"decoder": decoded.decoder_version, "synthetic": True,
                        "not_validated": True, "roi": decoded.roi},
            scientific_authorization="SIMULATED_ONLY (no scientific gate; not real neural data)",
            claim_level=self.claim_level)


class BehavioralObservationProvider(ObservationProvider):
    """Weak visual-embedding estimate derived from behavioral comparison against the current candidate.
    Lower quality than the neural provider; L1 (behavioral-assisted)."""
    source_type = SOURCE_BEHAVIORAL
    claim_level = L1_BEHAVIORAL_ASSISTED

    def __init__(self, imaginer: SyntheticImaginer):
        self.imaginer = imaginer

    def observe(self, context: dict) -> ObservationEnvelope:
        cand = context.get("current_candidate_embedding")
        prev = context.get("previous_candidate_embedding")
        if cand is None:
            raise ProviderUnavailableError("behavioral provider needs a current candidate")
        cmp = self.imaginer.compare(np.asarray(cand, float),
                                    None if prev is None else np.asarray(prev, float))
        # Behavioral "observation" is a coarse directional nudge toward/away from the presented candidate,
        # expressed as a high-variance pseudo-embedding observation.
        quality = 0.3
        return ObservationEnvelope(
            source_type=self.source_type,
            representation={"visual_direction": list(np.asarray(cand, float)),
                            "closer": cmp["closer"]},
            uncertainty={"visual": 1.5},
            signal_quality=quality,
            measurement_id=context.get("measurement_id", "behavioral"),
            timestamp=utcnow().isoformat(),
            provenance={"channel": "comparative", "synthetic_user": True},
            scientific_authorization="BEHAVIORAL_ONLY (no neural content)",
            claim_level=self.claim_level)


class ReplayObservationProvider(ObservationProvider):
    """Replays previously-recorded observation envelopes in order (exact replay)."""
    source_type = SOURCE_REPLAY
    claim_level = L0_SIMULATED

    def __init__(self, recorded: list[dict]):
        self._recorded = list(recorded)
        self._i = 0

    def observe(self, context: dict) -> ObservationEnvelope:
        if self._i >= len(self._recorded):
            raise ProviderUnavailableError("no more recorded observations")
        d = self._recorded[self._i]
        self._i += 1
        return ObservationEnvelope(
            source_type=self.source_type, representation=d["representation"],
            uncertainty=d["uncertainty"], signal_quality=d["signal_quality"],
            measurement_id=d["measurement_id"], timestamp=d["timestamp"],
            provenance={**d.get("provenance", {}), "replayed": True},
            scientific_authorization=d.get("scientific_authorization", "REPLAY"),
            claim_level=d.get("claim_level", L0_SIMULATED))


class FutureNeuralDecoderProvider(ObservationProvider):
    """Placeholder for a future VALIDATED neural decoder. NOT usable in ANIMUS-P1: constructing/observing
    fails closed unless a real, gate-authorized decoder is injected (never in this milestone)."""
    source_type = SOURCE_VALIDATED_NEURAL_FUTURE
    claim_level = L3_NEURAL_CONTENT_INFORMED_VALIDATED

    def __init__(self, decoder=None, authorization: str | None = None):
        self._decoder = decoder
        self._authorization = authorization

    def observe(self, context: dict) -> ObservationEnvelope:
        raise ProviderUnavailableError(
            "FutureNeuralDecoderProvider requires a scientifically-authorized validated decoder; "
            "unavailable in ANIMUS-P1 (fail-closed, no silent fallback)")


def build_provider(mode: str, imaginer: SyntheticImaginer | None = None,
                   calibration_seed: int = 0, dim: int = 16,
                   recorded: list[dict] | None = None) -> ObservationProvider:
    """Explicit provider factory. Unknown/unauthorized modes fail closed."""
    if mode == SOURCE_SIMULATED_NEURAL:
        return SyntheticNeuralObservationProvider(imaginer, calibration_seed, dim)
    if mode == SOURCE_BEHAVIORAL:
        return BehavioralObservationProvider(imaginer)
    if mode == SOURCE_REPLAY:
        return ReplayObservationProvider(recorded or [])
    if mode == SOURCE_VALIDATED_NEURAL_FUTURE:
        return FutureNeuralDecoderProvider()
    raise ProviderUnavailableError(f"unknown observation mode: {mode!r}")

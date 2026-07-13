"""Synthetic pipeline adapters — deterministic implementations for synthetic runtime.

Each adapter implements a protocol used by ResearchSessionRuntime, providing
deterministic behavior for synthetic sessions without real EEG or LSL.
"""
from __future__ import annotations

import math
from typing import Protocol


class SignalProvider(Protocol):
    provider_id: str
    provider_version: str

    async def start(self, session_id: str, seed: int) -> None: ...
    async def next_window(self, trial_idx: int, window_idx: int) -> dict[str, float]: ...
    async def stop(self) -> None: ...


class FeatureProcessor(Protocol):
    processor_id: str
    processor_version: str

    def process(self, raw_signals: dict[str, float]) -> dict[str, float]: ...


class StateEstimator(Protocol):
    estimator_id: str
    estimator_version: str

    def estimate(self, features: dict[str, float]) -> dict[str, float]: ...


class MetricProcessor(Protocol):
    processor_id: str
    processor_version: str

    def compute_pid(self, state: dict[str, float]) -> float: ...
    def compute_iqi(self, state: dict[str, float]) -> float: ...


class CurriculumProcessor(Protocol):
    processor_id: str
    processor_version: str

    def update(self, iqi: float, pid: float, trial_idx: int) -> int: ...


class DeterministicSignalProvider:
    provider_id = "synthetic.deterministic"
    provider_version = "1.0"

    def __init__(self) -> None:
        self._seed = 0

    async def start(self, session_id: str, seed: int) -> None:
        self._seed = seed

    async def next_window(self, trial_idx: int, window_idx: int) -> dict[str, float]:
        t = (trial_idx * 10 + window_idx + self._seed) * 0.1
        return {
            "alpha": 0.5 + 0.2 * math.sin(t),
            "beta": 0.4 + 0.15 * math.cos(t * 1.3),
            "theta": 0.3 + 0.1 * math.sin(t * 0.7),
            "gamma": 0.2 + 0.1 * math.cos(t * 2.1),
        }

    async def stop(self) -> None:
        pass


class PassthroughFeatureProcessor:
    processor_id = "passthrough"
    processor_version = "1.0"

    def process(self, raw_signals: dict[str, float]) -> dict[str, float]:
        return dict(raw_signals)


class RuleBasedStateEstimator:
    estimator_id = "rule_based"
    estimator_version = "1.0"

    def estimate(self, features: dict[str, float]) -> dict[str, float]:
        alpha = features.get("alpha", 0.5)
        beta = features.get("beta", 0.4)
        theta = features.get("theta", 0.3)
        gamma = features.get("gamma", 0.2)
        return {
            "attention": min(1.0, max(0.0, beta / (theta + 0.01))),
            "relaxation": min(1.0, max(0.0, alpha * 1.5)),
            "engagement": min(1.0, max(0.0, gamma * 2.0)),
            "fatigue": min(1.0, max(0.0, theta * 1.2)),
        }


class CompositeMetricProcessor:
    processor_id = "composite"
    processor_version = "1.0"

    def compute_pid(self, state: dict[str, float]) -> float:
        attention = state.get("attention", 0.5)
        return max(0.0, min(1.0, 1.0 - attention * 0.7))

    def compute_iqi(self, state: dict[str, float]) -> float:
        attention = state.get("attention", 0.5)
        engagement = state.get("engagement", 0.3)
        relaxation = state.get("relaxation", 0.5)
        return max(0.0, min(1.0, 0.35 * attention + 0.30 * engagement + 0.20 * relaxation + 0.15 * 0.5))


class FixedCurriculumProcessor:
    processor_id = "fixed_level"
    processor_version = "1.0"

    def __init__(self, level: int = 1) -> None:
        self._level = level

    def update(self, iqi: float, pid: float, trial_idx: int) -> int:
        return self._level

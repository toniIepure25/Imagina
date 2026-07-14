"""ResponseProvider interface for objective task responses.

Abstracts synthetic/recorded/future-human response generation.
Only SyntheticCognitiveResponseProvider is active in C0.1.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.research.cognitive_agent import (
    AgentScenario,
    AgentTraits,
    generate_trial_response,
)
from app.research.psychophysics.common import StimulusSpec

PROVIDER_VERSION = "1.0"


@dataclass
class ProviderConfig:
    provider_type: str
    version: str = PROVIDER_VERSION
    scenario_id: str = ""
    config_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


class ResponseProvider(ABC):
    @abstractmethod
    def generate_response(
        self,
        target: StimulusSpec,
        expected: StimulusSpec,
        condition: str,
        session_index: int,
        trial_index: int,
        is_perceptual_control: bool,
        seed: int,
        delay_s: float = 0.0,
        prev_condition: str | None = None,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_config(self) -> ProviderConfig:
        ...


class SyntheticCognitiveResponseProvider(ResponseProvider):
    def __init__(self, agent: AgentTraits, scenario: AgentScenario):
        self._agent = agent
        self._scenario = scenario

    def generate_response(
        self,
        target: StimulusSpec,
        expected: StimulusSpec,
        condition: str,
        session_index: int,
        trial_index: int,
        is_perceptual_control: bool,
        seed: int,
        delay_s: float = 0.0,
        prev_condition: str | None = None,
    ) -> dict[str, Any]:
        return generate_trial_response(
            self._agent, target, expected, condition, session_index,
            trial_index, self._scenario, is_perceptual_control, seed,
            delay_s=delay_s, prev_condition=prev_condition,
        )

    def get_config(self) -> ProviderConfig:
        data = json.dumps({
            "agent": self._agent.participant_id,
            "scenario": self._scenario.scenario_id,
            "version": PROVIDER_VERSION,
        }, sort_keys=True, separators=(",", ":"))
        return ProviderConfig(
            provider_type="synthetic_cognitive",
            scenario_id=self._scenario.scenario_id,
            config_hash=hashlib.sha256(data.encode()).hexdigest()[:16],
        )


class RecordedResponseProvider(ResponseProvider):
    """Replays previously recorded responses for exact replay verification."""

    def __init__(self, recorded_responses: list[dict[str, Any]]):
        self._responses = {
            (r["session_index"], r["trial_index"]): r for r in recorded_responses
        }

    def generate_response(
        self,
        target: StimulusSpec,
        expected: StimulusSpec,
        condition: str,
        session_index: int,
        trial_index: int,
        is_perceptual_control: bool,
        seed: int,
        delay_s: float = 0.0,
        prev_condition: str | None = None,
    ) -> dict[str, Any]:
        key = (session_index, trial_index)
        if key not in self._responses:
            raise KeyError(f"No recorded response for session {session_index}, trial {trial_index}")
        return self._responses[key]

    def get_config(self) -> ProviderConfig:
        return ProviderConfig(provider_type="recorded", config_hash="recorded")


class FutureHumanResponseProviderPlaceholder(ResponseProvider):
    """Placeholder for future human participant data collection."""

    def generate_response(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Human response provider not implemented in C0.1")

    def get_config(self) -> ProviderConfig:
        return ProviderConfig(provider_type="human_placeholder", config_hash="unimplemented")

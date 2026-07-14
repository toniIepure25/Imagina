"""Exact objective session replay and rescoring.

Reconstructs objective sessions from stable random streams, rescores
using the exact scoring version, and compares every component.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.cognitive_agent import AgentScenario, generate_population
from app.research.objective_provenance import CompletionSeal, ObjectiveManifest, create_completion_seal
from app.research.objective_runtime import (
    LeakageGuard,
    ObjectiveSessionResult,
    execute_objective_session,
)
from app.research.response_provider import SyntheticCognitiveResponseProvider

REPLAY_VERSION = "1.0"


@dataclass
class ReplayDivergence:
    field: str
    trial_index: int
    original: Any
    replayed: Any

    def to_dict(self) -> dict[str, Any]:
        return {k: str(v) for k, v in self.__dict__.items()}


@dataclass
class ReplayResult:
    session_id: str
    exact_match: bool
    divergences: list[ReplayDivergence] = field(default_factory=list)
    original_content_hash: str = ""
    replayed_content_hash: str = ""
    manifest_verified: bool = False
    seal_verified: bool = False
    replay_version: str = REPLAY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "exact_match": self.exact_match,
            "n_divergences": len(self.divergences),
            "divergences": [d.to_dict() for d in self.divergences],
            "original_content_hash": self.original_content_hash,
            "replayed_content_hash": self.replayed_content_hash,
            "manifest_verified": self.manifest_verified,
            "seal_verified": self.seal_verified,
        }


def replay_objective_session(
    original: ObjectiveSessionResult,
    manifest: ObjectiveManifest,
    seal: CompletionSeal,
    scenario: AgentScenario,
    trial_specs: list[dict[str, Any]],
    seed: int,
    prev_condition: str | None = None,
) -> ReplayResult:
    """Replay an objective session and verify exact reproduction."""
    result = ReplayResult(
        session_id=original.session_id,
        exact_match=False,
        original_content_hash=original.content_hash,
    )

    manifest_issues = manifest.validate()
    result.manifest_verified = len(manifest_issues) == 0

    seal_issues = []
    if seal.content_hash != original.content_hash:
        seal_issues.append("content_hash_mismatch")
    if seal.trial_count != len(original.trials):
        seal_issues.append("trial_count_mismatch")
    result.seal_verified = len(seal_issues) == 0

    pop = generate_population(1, seed=seed, scenario=scenario)
    if not pop:
        result.divergences.append(ReplayDivergence("population", -1, "expected", "empty"))
        return result

    agent = None
    for a in pop:
        if a.participant_id == original.participant_id:
            agent = a
            break
    if agent is None:
        agent = pop[0]

    provider = SyntheticCognitiveResponseProvider(agent, scenario)
    guard = LeakageGuard()

    replayed = execute_objective_session(
        original.session_id,
        original.participant_id,
        original.condition,
        original.period,
        trial_specs,
        provider,
        guard,
        seed,
        prev_condition=prev_condition,
    )

    result.replayed_content_hash = replayed.content_hash

    for i, (orig_t, rep_t) in enumerate(zip(original.trials, replayed.trials)):
        if orig_t.composite_error != rep_t.composite_error:
            result.divergences.append(ReplayDivergence(
                "composite_error", i, orig_t.composite_error, rep_t.composite_error,
            ))
        if orig_t.target != rep_t.target:
            result.divergences.append(ReplayDivergence("target", i, orig_t.target, rep_t.target))
        if orig_t.response != rep_t.response:
            result.divergences.append(ReplayDivergence("response", i, orig_t.response, rep_t.response))
        if orig_t.component_errors != rep_t.component_errors:
            result.divergences.append(ReplayDivergence(
                "component_errors", i, orig_t.component_errors, rep_t.component_errors,
            ))
        if orig_t.confidence != rep_t.confidence:
            result.divergences.append(ReplayDivergence("confidence", i, orig_t.confidence, rep_t.confidence))
        if orig_t.vividness != rep_t.vividness:
            result.divergences.append(ReplayDivergence("vividness", i, orig_t.vividness, rep_t.vividness))

    result.exact_match = len(result.divergences) == 0 and result.replayed_content_hash == result.original_content_hash

    return result


def replay_hash(result: ReplayResult) -> str:
    data = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()

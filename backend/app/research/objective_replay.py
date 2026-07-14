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


async def _reconstruct_session_from_db(db, session_id: str) -> ObjectiveSessionResult | None:
    """Reconstruct an ObjectiveSessionResult from persisted DB rows."""
    block = await (await db.execute(
        "SELECT * FROM objective_task_blocks WHERE session_id = ? LIMIT 1",
        (session_id,),
    )).fetchone()
    if not block:
        return None

    specs = await (await db.execute(
        "SELECT * FROM objective_trial_specs WHERE block_id = ? ORDER BY trial_index",
        (block["id"],),
    )).fetchall()

    from app.research.objective_runtime import ObjectiveSessionResult, ObjectiveTrialResult
    from app.research.objective_endpoints import registry_hash
    from app.research.psychophysics.scoring import SCORING_VERSION

    trials: list[ObjectiveTrialResult] = []
    for spec in specs:
        resp = await (await db.execute(
            "SELECT * FROM objective_trial_responses WHERE trial_spec_id = ?",
            (spec["id"],),
        )).fetchone()
        score = await (await db.execute(
            "SELECT * FROM objective_trial_scores WHERE trial_spec_id = ?",
            (spec["id"],),
        )).fetchone()

        if not resp or not score:
            continue

        trial_id = f"{session_id}-t{spec['trial_index']}-{spec['task_family']}"
        target = {
            "orientation_deg": spec["target_orientation"],
            "hue_deg": spec["target_hue"],
            "spatial_frequency_cpd": spec["target_sf"],
            "position_x": spec["target_pos_x"],
            "position_y": spec["target_pos_y"],
            "size": spec["target_size"],
        }
        response = {
            "orientation_deg": resp["response_orientation"],
            "hue_deg": resp["response_hue"],
            "spatial_frequency_cpd": resp["response_sf"],
            "position_x": resp["response_pos_x"],
            "position_y": resp["response_pos_y"],
            "size": resp["response_size"],
        }
        comp_errors = {
            "orientation": score["orientation_error"] or 0,
            "hue": score["hue_error"] or 0,
            "spatial_frequency": score["sf_error"] or 0,
            "position": score["position_error"] or 0,
            "size": score["size_error"] or 0,
        }

        trials.append(ObjectiveTrialResult(
            trial_id=trial_id,
            task_family=spec["task_family"],
            target=target,
            response=response,
            component_errors=comp_errors,
            composite_error=score["composite_error"] or 0,
            confidence=resp["confidence"] or 0,
            vividness=resp["vividness"] or 0,
            effort=resp["effort"] or 0,
            latency_ms=resp["response_latency_ms"] if "response_latency_ms" in resp.keys() else resp.get("latency_ms", 0),
            scoring_version=SCORING_VERSION,
            endpoint_registry_hash=score["endpoint_registry_hash"] or "",
        ))

    result = ObjectiveSessionResult(
        session_id=session_id,
        participant_id=block["participant_id"],
        condition=block["condition"],
        period=block["period"],
        trials=trials,
    )

    content = json.dumps(
        [t.to_dict() for t in result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    result.content_hash = hashlib.sha256(content.encode()).hexdigest()

    return result


async def replay_from_db(
    db,
    session_id: str,
    scenario: AgentScenario,
    trial_specs: list[dict[str, Any]],
    seed: int,
    prev_condition: str | None = None,
) -> ReplayResult:
    """Replay an objective session by reconstructing from DB and re-executing."""
    original = await _reconstruct_session_from_db(db, session_id)
    if not original:
        return ReplayResult(session_id=session_id, exact_match=False,
                            divergences=[ReplayDivergence("session", -1, "expected", "not_found")])

    seal_row = await (await db.execute(
        "SELECT * FROM objective_completion_seals WHERE session_id = ?",
        (session_id,),
    )).fetchone()

    manifest_row = await (await db.execute(
        "SELECT * FROM objective_manifests WHERE study_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    )).fetchone()

    manifest = ObjectiveManifest()
    if manifest_row:
        manifest_data = json.loads(manifest_row["manifest_json"])
        for k, v in manifest_data.items():
            if hasattr(manifest, k):
                setattr(manifest, k, v)

    seal = None
    if seal_row:
        seal = CompletionSeal(
            session_id=seal_row["session_id"],
            content_hash=seal_row["content_hash"],
            manifest_hash=seal_row["manifest_hash"],
            trial_count=seal_row["trial_count"],
            target_hash=seal_row["target_hash"],
            response_hash=seal_row["response_hash"],
            score_hash=seal_row["score_hash"],
            rating_hash=seal_row["rating_hash"],
            leakage_audit_hash=seal_row["leakage_audit_hash"],
            calibration_ref=seal_row["calibration_ref"] or "",
            valid=bool(seal_row["valid"]),
        )

    if seal:
        result = replay_objective_session(original, manifest, seal, scenario, trial_specs, seed, prev_condition)
    else:
        pop = generate_population(1, seed=seed, scenario=scenario)
        agent = pop[0] if pop else None
        if not agent:
            return ReplayResult(session_id=session_id, exact_match=False,
                                divergences=[ReplayDivergence("population", -1, "expected", "empty")])

        provider = SyntheticCognitiveResponseProvider(agent, scenario)
        guard = LeakageGuard()
        replayed = execute_objective_session(
            session_id, original.participant_id, original.condition,
            original.period, trial_specs, provider, guard, seed,
            prev_condition=prev_condition,
        )

        result = ReplayResult(
            session_id=session_id,
            exact_match=replayed.content_hash == original.content_hash,
            original_content_hash=original.content_hash,
            replayed_content_hash=replayed.content_hash,
        )
        for i, (o, r) in enumerate(zip(original.trials, replayed.trials)):
            if o.composite_error != r.composite_error:
                result.divergences.append(ReplayDivergence("composite_error", i, o.composite_error, r.composite_error))

    for d in result.divergences:
        await db.execute(
            """INSERT INTO replay_divergences
               (study_id, session_id, trial_index, field_name,
                original_value, replay_value, divergence_magnitude)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, session_id, d.trial_index, d.field,
             str(d.original), str(d.replayed), None),
        )
    await db.commit()

    return result

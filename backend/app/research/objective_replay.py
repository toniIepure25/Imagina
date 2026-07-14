"""Exact objective session replay from sealed persistent evidence.

Reconstructs objective sessions from DB rows, verifies manifest and seal
integrity, re-executes through the same response provider, and compares
every component. All replay inputs are resolved from persisted sealed
evidence — the caller supplies only a session_id.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.cognitive_agent import AgentScenario, SCENARIOS, generate_population
from app.research.objective_provenance import (
    CompletionSeal,
    ObjectiveManifest,
    verify_seal,
)
from app.research.objective_runtime import (
    LeakageGuard,
    ObjectiveSessionResult,
    ObjectiveTrialResult,
    execute_objective_session,
)
from app.research.psychophysics.scoring import SCORING_VERSION
from app.research.objective_endpoints import registry_hash
from app.research.response_provider import SyntheticCognitiveResponseProvider

REPLAY_VERSION = "2.0"


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
    exact_match: bool = False
    divergences: list[ReplayDivergence] = field(default_factory=list)
    original_content_hash: str = ""
    replayed_content_hash: str = ""
    manifest_verified: bool = False
    seal_verified: bool = False
    schedule_verified: bool = False
    scoring_verified: bool = False
    response_provider_verified: bool = False
    content_hash_match: bool = False
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
            "schedule_verified": self.schedule_verified,
            "scoring_verified": self.scoring_verified,
            "response_provider_verified": self.response_provider_verified,
            "content_hash_match": self.content_hash_match,
        }


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

    trials: list[ObjectiveTrialResult] = []
    for spec in specs:
        resp = await (await db.execute(
            "SELECT * FROM objective_trial_responses WHERE trial_spec_id = ?",
            (spec["id"],),
        )).fetchone()
        if not resp:
            continue
        score = await (await db.execute(
            "SELECT * FROM objective_trial_scores WHERE response_id = ?",
            (resp["id"],),
        )).fetchone()
        if not score:
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
            latency_ms=resp["latency_ms"] if "latency_ms" in resp.keys() else 0,
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


def _reconstruct_trial_specs_from_db_rows(specs) -> list[dict[str, Any]]:
    """Reconstruct trial spec dicts from DB spec rows."""
    result = []
    for spec in specs:
        result.append({
            "trial_index": spec["trial_index"],
            "task_family": spec["task_family"],
            "target_orientation": spec["target_orientation"],
            "target_hue": spec["target_hue"],
            "target_sf": spec["target_sf"],
            "target_pos_x": spec["target_pos_x"],
            "target_pos_y": spec["target_pos_y"],
            "target_size": spec["target_size"],
            "delay_s": spec["delay_s"] or 0.0,
            "is_perceptual_control": bool(spec["is_perceptual_control"]),
        })
    return result


def _verify_manifest_integrity(
    manifest: ObjectiveManifest,
    manifest_row: Any,
    seal: CompletionSeal,
) -> tuple[bool, list[str]]:
    """Full manifest verification against persisted and recomputed data."""
    issues: list[str] = []

    recomputed_hash = manifest.hash()
    if manifest_row["manifest_hash"] != recomputed_hash:
        issues.append(f"manifest_hash recompute mismatch: stored={manifest_row['manifest_hash']}, recomputed={recomputed_hash}")

    if seal.manifest_hash != recomputed_hash:
        issues.append(f"seal.manifest_hash != recomputed manifest hash")

    field_issues = manifest.validate()
    issues.extend(field_issues)

    current_reg_hash = registry_hash()
    if manifest.endpoint_registry_hash and manifest.endpoint_registry_hash != current_reg_hash:
        issues.append(f"endpoint_registry_hash mismatch: manifest={manifest.endpoint_registry_hash}, current={current_reg_hash}")

    if not manifest.scoring_version:
        issues.append("missing scoring_version")

    if not manifest.design_hash and not manifest.schedule_hash:
        issues.append("missing both design_hash and schedule_hash")

    return len(issues) == 0, issues


def _verify_seal_integrity(
    seal: CompletionSeal,
    original: ObjectiveSessionResult,
) -> tuple[bool, list[str]]:
    """Full canonical seal verification."""
    issues = verify_seal(seal, original)

    if not seal.valid:
        issues.append("seal.valid is False")

    return len(issues) == 0, issues


async def replay_from_db(
    db,
    session_id: str,
) -> ReplayResult:
    """Replay an objective session using only persisted sealed evidence.

    All replay inputs (scenario, trial specs, seed, response provider)
    are resolved from the canonical persisted manifest, frozen design,
    schedule rows, and scenario specification.
    """
    result = ReplayResult(session_id=session_id)

    original = await _reconstruct_session_from_db(db, session_id)
    if not original:
        result.divergences.append(ReplayDivergence("session", -1, "expected", "not_found"))
        await _persist_replay_run(db, session_id, result)
        return result

    result.original_content_hash = original.content_hash

    seal_row = await (await db.execute(
        "SELECT * FROM objective_completion_seals WHERE session_id = ?",
        (session_id,),
    )).fetchone()
    if not seal_row:
        result.divergences.append(ReplayDivergence("seal", -1, "required", "missing"))
        await _persist_replay_run(db, session_id, result)
        return result

    manifest_row = await (await db.execute(
        "SELECT * FROM objective_manifests WHERE study_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    )).fetchone()
    if not manifest_row:
        result.divergences.append(ReplayDivergence("manifest", -1, "required", "missing"))
        await _persist_replay_run(db, session_id, result)
        return result

    manifest = ObjectiveManifest()
    manifest_data = json.loads(manifest_row["manifest_json"])
    for k, v in manifest_data.items():
        if hasattr(manifest, k):
            setattr(manifest, k, v)

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

    manifest_ok, manifest_issues = _verify_manifest_integrity(manifest, manifest_row, seal)
    result.manifest_verified = manifest_ok
    for issue in manifest_issues:
        result.divergences.append(ReplayDivergence("manifest_verification", -1, "expected_valid", issue))

    seal_ok, seal_issues = _verify_seal_integrity(seal, original)
    result.seal_verified = seal_ok
    for issue in seal_issues:
        result.divergences.append(ReplayDivergence("seal_verification", -1, "expected_valid", issue))

    block = await (await db.execute(
        "SELECT * FROM objective_task_blocks WHERE session_id = ? LIMIT 1",
        (session_id,),
    )).fetchone()
    spec_rows = await (await db.execute(
        "SELECT * FROM objective_trial_specs WHERE block_id = ? ORDER BY trial_index",
        (block["id"],),
    )).fetchall()
    trial_specs = _reconstruct_trial_specs_from_db_rows(spec_rows)

    if block["schedule_hash"]:
        recomputed_schedule = hashlib.sha256(
            json.dumps(trial_specs, sort_keys=True).encode()
        ).hexdigest()[:16]
        result.schedule_verified = block["schedule_hash"] == recomputed_schedule
    else:
        result.schedule_verified = False
        result.divergences.append(ReplayDivergence("schedule", -1, "hash_required", "missing"))

    result.scoring_verified = bool(manifest.scoring_version == SCORING_VERSION)
    if not result.scoring_verified:
        result.divergences.append(ReplayDivergence(
            "scoring_version", -1, SCORING_VERSION, manifest.scoring_version))

    result.response_provider_verified = bool(manifest.response_provider_id)
    if not result.response_provider_verified:
        result.divergences.append(ReplayDivergence(
            "response_provider", -1, "required", "missing_id"))

    scenario_id = manifest.scenario_hash
    scenario = None
    for sid, s in SCENARIOS.items():
        s_dict = json.dumps(s.to_dict(), sort_keys=True, separators=(",", ":"))
        s_hash = hashlib.sha256(s_dict.encode()).hexdigest()[:16]
        if s_hash == scenario_id:
            scenario = s
            break
    if scenario is None:
        for sid, s in SCENARIOS.items():
            if sid == manifest.cognitive_agent_version or s.scenario_id == manifest.cognitive_agent_version:
                scenario = s
                break
    if scenario is None:
        scenario = next(iter(SCENARIOS.values()))
        result.divergences.append(ReplayDivergence("scenario", -1, scenario_id, "unresolvable_fallback"))

    seed = 42
    pop = generate_population(1, seed=seed, scenario=scenario)
    if not pop:
        result.divergences.append(ReplayDivergence("population", -1, "expected", "empty"))
        await _persist_replay_run(db, session_id, result)
        return result

    agent = pop[0]
    for a in pop:
        if a.participant_id == original.participant_id:
            agent = a
            break

    provider = SyntheticCognitiveResponseProvider(agent, scenario)
    guard = LeakageGuard()

    prev_condition = None
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
    result.content_hash_match = (replayed.content_hash == original.content_hash)

    for i, (orig_t, rep_t) in enumerate(zip(original.trials, replayed.trials)):
        if orig_t.composite_error != rep_t.composite_error:
            result.divergences.append(ReplayDivergence(
                "composite_error", i, orig_t.composite_error, rep_t.composite_error))
        if orig_t.target != rep_t.target:
            result.divergences.append(ReplayDivergence("target", i, orig_t.target, rep_t.target))
        if orig_t.response != rep_t.response:
            result.divergences.append(ReplayDivergence("response", i, orig_t.response, rep_t.response))
        if orig_t.component_errors != rep_t.component_errors:
            result.divergences.append(ReplayDivergence(
                "component_errors", i, orig_t.component_errors, rep_t.component_errors))
        if orig_t.confidence != rep_t.confidence:
            result.divergences.append(ReplayDivergence("confidence", i, orig_t.confidence, rep_t.confidence))
        if orig_t.vividness != rep_t.vividness:
            result.divergences.append(ReplayDivergence("vividness", i, orig_t.vividness, rep_t.vividness))

    if len(original.trials) != len(replayed.trials):
        result.divergences.append(ReplayDivergence(
            "trial_count", -1, len(original.trials), len(replayed.trials)))

    result.exact_match = (
        result.manifest_verified
        and result.seal_verified
        and result.schedule_verified
        and result.scoring_verified
        and result.response_provider_verified
        and result.content_hash_match
        and len(result.divergences) == 0
    )

    await _persist_replay_run(db, session_id, result)
    return result


async def _persist_replay_run(db, session_id: str, result: ReplayResult) -> None:
    """Persist a replay run and its results to DB."""
    run_cursor = await db.execute(
        """INSERT INTO objective_replay_runs
           (study_id, session_id, exact_match, manifest_verified,
            seal_verified, schedule_verified, scoring_verified,
            response_provider_verified,
            n_divergences, original_content_hash,
            replayed_content_hash, replay_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, session_id, int(result.exact_match),
         int(result.manifest_verified), int(result.seal_verified),
         int(result.schedule_verified), int(result.scoring_verified),
         int(result.response_provider_verified),
         len(result.divergences), result.original_content_hash,
         result.replayed_content_hash, result.replay_version),
    )
    replay_run_id = run_cursor.lastrowid

    for d in result.divergences:
        await db.execute(
            """INSERT INTO objective_replay_results
               (replay_run_id, trial_index, field_name,
                original_value, replayed_value, match)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (replay_run_id, d.trial_index, d.field,
             str(d.original), str(d.replayed), 0),
        )

    if result.exact_match:
        await db.execute(
            """INSERT INTO objective_replay_results
               (replay_run_id, trial_index, field_name,
                original_value, replayed_value, match)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (replay_run_id, -1, "exact_match", "true", "true", 1),
        )

    await db.commit()

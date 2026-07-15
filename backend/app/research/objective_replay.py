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

from app.research.cognitive_agent import SCENARIOS, generate_population
from app.research.objective_endpoints import registry_hash
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
from app.research.response_provider import SyntheticCognitiveResponseProvider
from app.research.rng_registry import RNG_VERSION, rng_version_hash

REPLAY_VERSION = "3.0"

# Provider types replay is able to instantiate and verify. A manifest naming
# any other response_provider_id cannot be replayed and must fail closed.
_PROVIDER_REGISTRY = {
    "synthetic_cognitive": SyntheticCognitiveResponseProvider,
}

# Manifest keys that must be explicitly present as JSON keys (even if their
# value is legitimately null), distinguishing "field absent" from "field
# explicitly present with null". Absence of any of these is a structured
# divergence that stops replay before any further verification is attempted.
_REQUIRED_MANIFEST_KEYS = (
    "root_seed",
    "participant_generation_index",
    "previous_condition",
    "scenario_id",
    "scenario_hash",
    "response_provider_id",
    "response_provider_version",
    "response_provider_config_hash",
    "rng_version",
    "rng_version_hash",
    "scoring_version",
    "scoring_hash",
    "schedule_hash",
    "design_hash",
)


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
            "orientation_deg": float(spec["target_orientation"]),
            "hue_deg": float(spec["target_hue"]),
            "spatial_frequency_cpd": float(spec["target_sf"]),
            "position_x": float(spec["target_pos_x"]),
            "position_y": float(spec["target_pos_y"]),
            "size": float(spec["target_size"]),
        }
        response = {
            "orientation_deg": resp["response_orientation"],
            "hue_deg": resp["response_hue"],
            "spatial_frequency_cpd": resp["response_sf"],
            "position_x": resp["response_pos_x"],
            "position_y": resp["response_pos_y"],
            "size": resp["response_size"],
            "latency_ms": resp["latency_ms"] if "latency_ms" in resp.keys() else 0,
        }
        comp_errors = {
            "orientation": float(score["orientation_error"] or 0),
            "hue": float(score["hue_error"] or 0),
            "spatial_frequency": float(score["sf_error"] or 0),
            "position": float(score["position_error"] or 0),
            "size": float(score["size_error"] or 0),
        }

        trials.append(ObjectiveTrialResult(
            trial_id=trial_id,
            task_family=spec["task_family"],
            target=target,
            response=response,
            component_errors=comp_errors,
            composite_error=float(score["composite_error"] or 0),
            confidence=float(resp["confidence"] or 0),
            vividness=float(resp["vividness"] or 0),
            effort=float(resp["effort"] or 0),
            latency_ms=float(resp["latency_ms"]) if "latency_ms" in resp.keys() else 0.0,
            scoring_version=SCORING_VERSION,
            endpoint_registry_hash=score["endpoint_registry_hash"] or "",
        ))

    from app.research.objective_runtime import LeakageAuditRecord

    leakage_audits: list[LeakageAuditRecord] = []
    audit_rows = await (await db.execute(
        "SELECT * FROM objective_leakage_audits WHERE block_id = ?",
        (block["id"],),
    )).fetchall()
    for arow in audit_rows:
        leakage_audits.append(LeakageAuditRecord(
            trial_id=arow["trial_id"],
            policy_input_fields=json.loads(arow["policy_fields"]) if arow["policy_fields"] else [],
            forbidden_fields_checked=json.loads(arow["checked_fields"]) if arow["checked_fields"] else [],
            violations=json.loads(arow["violations"]) if arow["violations"] else [],
            passed=bool(arow["passed"]),
        ))

    result = ObjectiveSessionResult(
        session_id=session_id,
        participant_id=block["participant_id"],
        condition=block["condition"],
        period=block["period"],
        trials=trials,
        leakage_audit=leakage_audits,
    )

    content = json.dumps(
        [t.to_dict() for t in result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    result.content_hash = hashlib.sha256(content.encode()).hexdigest()

    return result


def _reconstruct_trial_specs_from_db_rows(specs) -> list[dict[str, Any]]:
    """Reconstruct trial spec dicts from DB spec rows, normalized for consistent hashing."""
    result = []
    for spec in specs:
        result.append({
            "trial_index": spec["trial_index"],
            "task_family": spec["task_family"],
            "target_orientation": float(spec["target_orientation"]),
            "target_hue": float(spec["target_hue"]),
            "target_sf": float(spec["target_sf"]),
            "target_pos_x": float(spec["target_pos_x"]),
            "target_pos_y": float(spec["target_pos_y"]),
            "target_size": float(spec["target_size"]),
            "delay_s": float(spec["delay_s"] or 0),
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
        issues.append(
            f"manifest_hash recompute mismatch: stored={manifest_row['manifest_hash']}, "
            f"recomputed={recomputed_hash}"
        )

    if seal.manifest_hash != recomputed_hash:
        issues.append("seal.manifest_hash != recomputed manifest hash")

    field_issues = manifest.validate()
    issues.extend(field_issues)

    current_reg_hash = registry_hash()
    if manifest.endpoint_registry_hash and manifest.endpoint_registry_hash != current_reg_hash:
        issues.append(
            f"endpoint_registry_hash mismatch: manifest={manifest.endpoint_registry_hash}, "
            f"current={current_reg_hash}"
        )

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


def _resolve_scenario(manifest: ObjectiveManifest):
    """Resolve scenario from manifest. Returns (scenario, issues).

    Strict resolution only: the scenario_id must be present and registered,
    and the computed scenario hash must equal the manifest's scenario_hash.
    cognitive_agent_version is implementation metadata only and is never used
    to resolve scenario identity.
    """
    scenario_id_val = manifest.scenario_id
    scenario_hash_val = manifest.scenario_hash

    if not scenario_id_val:
        return None, ["missing scenario_id in manifest"]

    if scenario_id_val not in SCENARIOS:
        return None, [f"unregistered scenario_id: {scenario_id_val}"]

    candidate = SCENARIOS[scenario_id_val]
    s_dict = json.dumps(candidate.to_dict(), sort_keys=True, separators=(",", ":"))
    s_hash = hashlib.sha256(s_dict.encode()).hexdigest()[:16]

    if not scenario_hash_val or s_hash != scenario_hash_val:
        return None, [f"scenario_hash mismatch: manifest={scenario_hash_val}, computed={s_hash}"]

    return candidate, []


async def replay_from_db(
    db,
    session_id: str,
) -> ReplayResult:
    """Replay an objective session using only persisted sealed evidence.

    All replay inputs (scenario, trial specs, seed, response provider,
    previous condition) are resolved from the canonical persisted manifest.
    No defaults are used — missing values produce structured divergences.
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

    manifest_data = json.loads(manifest_row["manifest_json"])

    missing_keys = [k for k in _REQUIRED_MANIFEST_KEYS if k not in manifest_data]
    if missing_keys:
        for k in missing_keys:
            result.divergences.append(ReplayDivergence(k, -1, "present", "absent"))
        await _persist_replay_run(db, session_id, result)
        return result

    manifest = ObjectiveManifest()
    for k, v in manifest_data.items():
        if hasattr(manifest, k):
            setattr(manifest, k, v)

    if original.period > 0 and manifest.previous_condition is None:
        result.divergences.append(ReplayDivergence(
            "previous_condition", -1, "non_null_required_period_gt_0", "null"))
        await _persist_replay_run(db, session_id, result)
        return result

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

    schedule_hash_db = block["schedule_hash"] if block["schedule_hash"] else None
    schedule_hash_manifest = manifest.schedule_hash if manifest.schedule_hash else None

    if schedule_hash_db and schedule_hash_manifest:
        recomputed_schedule = hashlib.sha256(
            json.dumps(trial_specs, sort_keys=True).encode()
        ).hexdigest()[:16]
        result.schedule_verified = (
            schedule_hash_db == recomputed_schedule
            and schedule_hash_manifest == recomputed_schedule
        )
        if not result.schedule_verified:
            result.divergences.append(ReplayDivergence(
                "schedule_hash", -1,
                f"db={schedule_hash_db},manifest={schedule_hash_manifest}",
                f"recomputed={recomputed_schedule}",
            ))
    else:
        result.schedule_verified = False
        result.divergences.append(ReplayDivergence("schedule", -1, "hash_required", "missing"))

    result.scoring_verified = bool(manifest.scoring_version == SCORING_VERSION)
    if not result.scoring_verified:
        result.divergences.append(ReplayDivergence(
            "scoring_version", -1, SCORING_VERSION, manifest.scoring_version))

    scenario, scenario_issues = _resolve_scenario(manifest)
    if scenario is None:
        for issue in scenario_issues:
            result.divergences.append(ReplayDivergence("scenario", -1, "resolvable", issue))
        await _persist_replay_run(db, session_id, result)
        return result

    seed = manifest.root_seed
    if seed is None:
        result.divergences.append(ReplayDivergence("root_seed", -1, "required", "null"))
        await _persist_replay_run(db, session_id, result)
        return result

    prev_condition = manifest.previous_condition

    rng_ok = (
        manifest.rng_version == RNG_VERSION
        and manifest.rng_version_hash == rng_version_hash()
    )
    if not rng_ok:
        result.divergences.append(ReplayDivergence(
            "rng_version", -1,
            f"{RNG_VERSION}/{rng_version_hash()}",
            f"{manifest.rng_version}/{manifest.rng_version_hash}",
        ))
        await _persist_replay_run(db, session_id, result)
        return result

    gen_index = manifest.participant_generation_index
    if not isinstance(gen_index, int) or isinstance(gen_index, bool) or gen_index < 0:
        result.divergences.append(ReplayDivergence(
            "participant_generation_index", -1, "required_nonneg_int", str(gen_index)))
        await _persist_replay_run(db, session_id, result)
        return result

    pop = generate_population(gen_index + 1, seed=seed, scenario=scenario)
    if not pop or gen_index >= len(pop):
        result.divergences.append(ReplayDivergence("population", -1, "expected", "empty_or_index_oob"))
        await _persist_replay_run(db, session_id, result)
        return result

    # Resolve the exact participant generated at the manifest's index. Do not
    # search the population for a matching participant_id — a mismatch here
    # is a structured divergence, not something to silently paper over.
    agent = pop[gen_index]
    if agent.participant_id != original.participant_id:
        result.divergences.append(ReplayDivergence(
            "participant_generation_index", -1, original.participant_id, agent.participant_id))
        await _persist_replay_run(db, session_id, result)
        return result

    provider_cls = _PROVIDER_REGISTRY.get(manifest.response_provider_id)
    if provider_cls is None:
        result.divergences.append(ReplayDivergence(
            "response_provider", -1, "known_provider_type", manifest.response_provider_id or "missing"))
        await _persist_replay_run(db, session_id, result)
        return result

    provider = provider_cls(agent, scenario)
    provider_config = provider.get_config()
    result.response_provider_verified = (
        manifest.response_provider_id == provider_config.provider_type
        and manifest.response_provider_version == provider_config.version
        and manifest.response_provider_config_hash == provider_config.config_hash
    )
    if not result.response_provider_verified:
        result.divergences.append(ReplayDivergence(
            "response_provider", -1,
            f"id={manifest.response_provider_id},version={manifest.response_provider_version},"
            f"config_hash={manifest.response_provider_config_hash}",
            f"id={provider_config.provider_type},version={provider_config.version},"
            f"config_hash={provider_config.config_hash}",
        ))

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
            response_provider_verified, content_hash_match,
            n_divergences, original_content_hash,
            replayed_content_hash, replay_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, session_id, int(result.exact_match),
         int(result.manifest_verified), int(result.seal_verified),
         int(result.schedule_verified), int(result.scoring_verified),
         int(result.response_provider_verified), int(result.content_hash_match),
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

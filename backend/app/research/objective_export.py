"""Complete objective scientific evidence package export and validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.objective_endpoints import registry_hash
from app.research.psychophysics.scoring import SCORING_VERSION

EXPORT_VERSION = "1.0"


@dataclass
class ExportPackage:
    study_id: str
    endpoint_registry_snapshot: dict[str, Any] = field(default_factory=dict)
    endpoint_registry_hash: str = ""
    scoring_hash: str = ""
    scoring_version: str = SCORING_VERSION
    calibrations: list[dict[str, Any]] = field(default_factory=list)
    calibration_hash: str = ""
    frozen_schedules: list[dict[str, Any]] = field(default_factory=list)
    schedule_hash: str = ""
    objective_targets: list[dict[str, Any]] = field(default_factory=list)
    responses: list[dict[str, Any]] = field(default_factory=list)
    component_scores: list[dict[str, Any]] = field(default_factory=list)
    composite_scores: list[dict[str, Any]] = field(default_factory=list)
    subjective_outcomes: list[dict[str, Any]] = field(default_factory=list)
    negative_controls: list[dict[str, Any]] = field(default_factory=list)
    analysis_specification: dict[str, Any] = field(default_factory=dict)
    analysis_spec_hash: str = ""
    analysis_results: list[dict[str, Any]] = field(default_factory=list)
    simulation_config: dict[str, Any] = field(default_factory=dict)
    replicate_summaries: list[dict[str, Any]] = field(default_factory=list)
    oracle_estimands: list[dict[str, Any]] = field(default_factory=list)
    oracle_spec_hash: str = ""
    operating_characteristics: dict[str, Any] = field(default_factory=dict)
    reliability_results: dict[str, Any] = field(default_factory=dict)
    manifest_evidence: list[dict[str, Any]] = field(default_factory=list)
    seal_evidence: list[dict[str, Any]] = field(default_factory=list)
    replay_results: list[dict[str, Any]] = field(default_factory=list)
    version: str = EXPORT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def export_hash(package: ExportPackage) -> str:
    data = json.dumps(package.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


async def build_export_from_db(db, study_id: str) -> ExportPackage:
    """Build a complete ExportPackage from persisted DB evidence."""
    package = ExportPackage(study_id=study_id)
    package.endpoint_registry_hash = registry_hash()

    blocks = await (await db.execute(
        "SELECT * FROM objective_task_blocks WHERE study_id = ?", (study_id,),
    )).fetchall()

    for block in blocks:
        specs = await (await db.execute(
            "SELECT * FROM objective_trial_specs WHERE block_id = ? ORDER BY trial_index",
            (block["id"],),
        )).fetchall()
        for spec in specs:
            package.objective_targets.append({
                "block_id": block["id"], "trial_index": spec["trial_index"],
                "task_family": spec["task_family"],
                "orientation": spec["target_orientation"], "hue": spec["target_hue"],
                "sf": spec["target_sf"], "pos_x": spec["target_pos_x"],
                "pos_y": spec["target_pos_y"], "size": spec["target_size"],
            })

            resp = await (await db.execute(
                "SELECT * FROM objective_trial_responses WHERE trial_spec_id = ?", (spec["id"],),
            )).fetchone()
            if resp:
                package.responses.append({
                    "trial_spec_id": spec["id"],
                    "orientation": resp["response_orientation"], "hue": resp["response_hue"],
                    "sf": resp["response_sf"], "pos_x": resp["response_pos_x"],
                    "pos_y": resp["response_pos_y"], "size": resp["response_size"],
                    "confidence": resp["confidence"], "vividness": resp["vividness"],
                    "effort": resp["effort"],
                })
                package.subjective_outcomes.append({
                    "trial_spec_id": spec["id"],
                    "confidence": resp["confidence"], "vividness": resp["vividness"],
                    "effort": resp["effort"],
                })

            score_row = None
            if resp:
                score_row = await (await db.execute(
                    "SELECT * FROM objective_trial_scores WHERE response_id = ?", (resp["id"],),
                )).fetchone()
            score = score_row
            if score:
                package.component_scores.append({
                    "trial_spec_id": spec["id"],
                    "orientation_error": score["orientation_error"],
                    "hue_error": score["hue_error"],
                    "sf_error": score["sf_error"],
                    "position_error": score["position_error"],
                    "size_error": score["size_error"],
                })
                package.composite_scores.append({
                    "trial_spec_id": spec["id"],
                    "composite_error": score["composite_error"],
                    "scoring_version": score["scoring_version"],
                })

    cals = await (await db.execute(
        "SELECT * FROM objective_calibrations WHERE study_id = ?", (study_id,),
    )).fetchall()
    package.calibrations = [dict(c) for c in cals]
    if cals:
        cal_data = json.dumps([dict(c) for c in cals], sort_keys=True, separators=(",", ":"), default=str)
        package.calibration_hash = hashlib.sha256(cal_data.encode()).hexdigest()[:16]

    sim_runs = await (await db.execute(
        "SELECT * FROM simulation_runs WHERE study_id = ? AND status = 'completed'",
        (study_id,),
    )).fetchall()
    for run in sim_runs:
        summary = await (await db.execute(
            "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (run["id"],),
        )).fetchone()
        if summary:
            package.replicate_summaries.append(json.loads(summary["summary_json"]))

    oracles = await (await db.execute(
        "SELECT * FROM oracle_estimands WHERE study_id = ? OR scenario_id = ?",
        (study_id, study_id),
    )).fetchall()
    package.oracle_estimands = [dict(o) for o in oracles]
    if oracles:
        package.oracle_spec_hash = oracles[0]["spec_hash"] or ""

    specs = await (await db.execute(
        "SELECT * FROM analysis_specifications WHERE study_id = ?",
        (study_id,),
    )).fetchall()
    if specs:
        package.analysis_specification = dict(specs[0])
        package.analysis_spec_hash = specs[0]["spec_hash"]

    a_runs = await (await db.execute(
        "SELECT ar.* FROM analysis_runs ar JOIN analysis_specifications asp ON ar.spec_id = asp.id WHERE asp.study_id = ?",
        (study_id,),
    )).fetchall()
    for run in a_runs:
        results = await (await db.execute(
            "SELECT * FROM analysis_results WHERE run_id = ?", (run["id"],),
        )).fetchall()
        for r in results:
            package.analysis_results.append(json.loads(r["result_json"]) if r["result_json"] else dict(r))

    manifests = await (await db.execute(
        "SELECT * FROM objective_manifests WHERE study_id = ?", (study_id,),
    )).fetchall()
    package.manifest_evidence = [json.loads(m["manifest_json"]) for m in manifests]

    seals = await (await db.execute(
        "SELECT * FROM objective_completion_seals WHERE study_id = ?", (study_id,),
    )).fetchall()
    package.seal_evidence = [json.loads(s["seal_json"]) for s in seals]

    replay_runs = await (await db.execute(
        "SELECT * FROM objective_replay_runs WHERE study_id = ?", (study_id,),
    )).fetchall()
    for rr in replay_runs:
        rr_results = await (await db.execute(
            "SELECT * FROM objective_replay_results WHERE replay_run_id = ?", (rr["id"],),
        )).fetchall()
        package.replay_results.append({
            "replay_run_id": rr["id"],
            "session_id": rr["session_id"],
            "exact_match": bool(rr["exact_match"]),
            "manifest_verified": bool(rr["manifest_verified"]),
            "seal_verified": bool(rr["seal_verified"]),
            "n_divergences": rr["n_divergences"],
            "results": [dict(r) for r in rr_results],
        })

    return package


def validate_export_package(package: ExportPackage) -> ValidationResult:
    """Validate completeness and integrity of an export package."""
    issues: list[str] = []
    checks = 0
    passed = 0

    checks += 1
    if package.endpoint_registry_hash:
        expected = registry_hash()
        if package.endpoint_registry_hash == expected:
            passed += 1
        else:
            issues.append(f"endpoint_registry_hash mismatch: {package.endpoint_registry_hash} != {expected}")
    else:
        issues.append("missing endpoint_registry_hash")

    checks += 1
    if package.scoring_version:
        passed += 1
    else:
        issues.append("missing scoring_version")

    checks += 1
    if package.schedule_hash:
        passed += 1
    else:
        issues.append("missing schedule_hash")

    checks += 1
    if package.analysis_spec_hash:
        passed += 1
    else:
        issues.append("missing analysis_spec_hash")

    checks += 1
    if package.oracle_spec_hash:
        passed += 1
    else:
        issues.append("missing oracle_spec_hash")

    checks += 1
    if package.objective_targets:
        passed += 1
    else:
        issues.append("no objective_targets")

    checks += 1
    if package.responses:
        passed += 1
    else:
        issues.append("no responses")

    checks += 1
    if package.composite_scores:
        passed += 1
    else:
        issues.append("no composite_scores")

    checks += 1
    if package.seal_evidence:
        passed += 1
    else:
        issues.append("no seal_evidence")

    checks += 1
    if package.replay_results:
        passed += 1
    else:
        issues.append("no replay_results")

    checks += 1
    if package.manifest_evidence:
        passed += 1
    else:
        issues.append("no manifest_evidence")

    checks += 1
    n_targets = len(package.objective_targets)
    n_responses = len(package.responses)
    if n_targets > 0 and n_targets == n_responses:
        passed += 1
    elif n_targets != n_responses:
        issues.append(f"target/response count mismatch: {n_targets} vs {n_responses}")

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        checks_passed=passed,
        checks_total=checks,
    )

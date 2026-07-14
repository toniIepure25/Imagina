"""Complete objective scientific evidence package export and validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.objective_endpoints import registry_hash
from app.research.psychophysics.scoring import SCORING_VERSION

EXPORT_VERSION = "2.0"


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
    design_hash: str = ""
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
    leakage_audits: list[dict[str, Any]] = field(default_factory=list)
    trial_transitions: list[dict[str, Any]] = field(default_factory=list)
    outbox_events: list[dict[str, Any]] = field(default_factory=list)
    campaign_id: str = ""
    campaign_valid: bool = False
    inference_valid: bool = False
    estimand_ids: list[str] = field(default_factory=list)
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
        if block["schedule_hash"]:
            package.schedule_hash = block["schedule_hash"]

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
            if score_row:
                package.component_scores.append({
                    "trial_spec_id": spec["id"],
                    "orientation_error": score_row["orientation_error"],
                    "hue_error": score_row["hue_error"],
                    "sf_error": score_row["sf_error"],
                    "position_error": score_row["position_error"],
                    "size_error": score_row["size_error"],
                })
                package.composite_scores.append({
                    "trial_spec_id": spec["id"],
                    "composite_error": score_row["composite_error"],
                    "scoring_version": score_row["scoring_version"],
                })

        audits = await (await db.execute(
            "SELECT * FROM objective_leakage_audits WHERE block_id = ?", (block["id"],),
        )).fetchall()
        for a in audits:
            package.leakage_audits.append(dict(a))

        transitions = await (await db.execute(
            "SELECT * FROM objective_trial_transitions WHERE block_id = ?", (block["id"],),
        )).fetchall()
        for t in transitions:
            package.trial_transitions.append(dict(t))

        outbox = await (await db.execute(
            "SELECT * FROM objective_outbox_events WHERE block_id = ?", (block["id"],),
        )).fetchall()
        for o in outbox:
            package.outbox_events.append(dict(o))

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
            summary_data = json.loads(summary["summary_json"])
            package.replicate_summaries.append(summary_data)
            if summary_data.get("campaign_valid") is not None:
                package.campaign_valid = summary_data["campaign_valid"]
            if run.get("study_id"):
                package.campaign_id = run["study_id"]

    oracles = await (await db.execute(
        "SELECT * FROM oracle_estimands WHERE scenario_id = ?",
        (study_id,),
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
        if specs[0]["estimand_id"]:
            package.estimand_ids.append(specs[0]["estimand_id"])

    a_runs = await (await db.execute(
        "SELECT ar.* FROM analysis_runs ar JOIN analysis_specifications asp ON ar.spec_id = asp.id WHERE asp.study_id = ?",
        (study_id,),
    )).fetchall()
    for run in a_runs:
        results = await (await db.execute(
            "SELECT * FROM analysis_results WHERE run_id = ?", (run["id"],),
        )).fetchall()
        for r in results:
            result_data = json.loads(r["result_json"]) if r["result_json"] else dict(r)
            package.analysis_results.append(result_data)
            if r["inference_valid"]:
                package.inference_valid = True

    manifests = await (await db.execute(
        "SELECT * FROM objective_manifests WHERE study_id = ?", (study_id,),
    )).fetchall()
    package.manifest_evidence = [json.loads(m["manifest_json"]) for m in manifests]
    if manifests:
        package.design_hash = json.loads(manifests[0]["manifest_json"]).get("design_hash", "")
        package.scoring_hash = json.loads(manifests[0]["manifest_json"]).get("scoring_hash", "")

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
            "schedule_verified": bool(rr["schedule_verified"]),
            "scoring_verified": bool(rr["scoring_verified"]),
            "response_provider_verified": bool(rr["response_provider_verified"]),
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
    if package.design_hash:
        passed += 1
    else:
        issues.append("missing design_hash")

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
    if package.manifest_evidence:
        passed += 1
    else:
        issues.append("no manifest_evidence")

    checks += 1
    n_targets = len(package.objective_targets)
    n_responses = len(package.responses)
    n_scores = len(package.composite_scores)
    if n_targets > 0 and n_targets == n_responses == n_scores:
        passed += 1
    else:
        issues.append(f"target/response/score count mismatch: {n_targets}/{n_responses}/{n_scores}")

    checks += 1
    if package.manifest_evidence and package.seal_evidence:
        for seal_ev in package.seal_evidence:
            manifest_hash_in_seal = seal_ev.get("manifest_hash", "")
            found = any(
                hashlib.sha256(
                    json.dumps(m, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest() == manifest_hash_in_seal
                for m in package.manifest_evidence
            )
            if not found and manifest_hash_in_seal:
                issues.append("manifest_hash in seal does not match any manifest evidence")
                break
        if "manifest_hash in seal does not match any manifest evidence" not in issues:
            passed += 1
    else:
        issues.append("cannot verify manifest/seal hash agreement — missing evidence")

    checks += 1
    has_successful_replay = False
    for rr in package.replay_results:
        if rr.get("exact_match"):
            if not rr.get("manifest_verified") or not rr.get("seal_verified"):
                issues.append("replay marked exact_match but verification flags are false")
                break
            has_successful_replay = True
    if has_successful_replay:
        passed += 1
    elif package.objective_targets:
        issues.append("no successful replay evidence for completed objective session")

    checks += 1
    if package.leakage_audits:
        passed += 1
    else:
        issues.append("no leakage_audits")

    checks += 1
    if package.trial_transitions:
        passed += 1
    else:
        issues.append("no trial_transitions")

    checks += 1
    n_outbox = len(package.outbox_events)
    n_trials = len(package.objective_targets)
    if n_outbox > 0 and n_trials > 0:
        expected_outbox = n_trials * 4 + 1
        if n_outbox == expected_outbox:
            passed += 1
        else:
            issues.append(f"outbox/domain count inconsistent: {n_outbox} outbox vs {expected_outbox} expected")
    elif n_trials > 0:
        issues.append("no outbox_events")
    else:
        passed += 1

    checks += 1
    if package.inference_valid:
        passed += 1
    else:
        issues.append("confirmatory analysis has inference_valid=false")

    checks += 1
    if package.campaign_valid:
        passed += 1
    else:
        issues.append("campaign has overall_pass=false")

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        checks_passed=passed,
        checks_total=checks,
    )

"""Objective measurement provenance for session manifests and completion seals.

Extends the persistent session manifest with objective measurement and
analysis provenance. The completion seal covers objective targets, responses,
scores, and leakage audit.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.objective_endpoints import REGISTRY_VERSION, registry_hash
from app.research.objective_runtime import (
    OBJECTIVE_RUNTIME_VERSION,
    ObjectiveSessionResult,
    compute_objective_manifest_hash,
    manifest_objective_fields,
)
from app.research.psychophysics.calibration import CALIBRATION_VERSION
from app.research.psychophysics.common import BATTERY_VERSION
from app.research.psychophysics.scoring import SCORING_VERSION
from app.research.rng_registry import RNG_VERSION, rng_version_hash

PROVENANCE_VERSION = "1.0"


@dataclass
class ObjectiveManifest:
    """Complete objective measurement manifest for a study session."""
    battery_version: str = BATTERY_VERSION
    endpoint_registry_version: str = REGISTRY_VERSION
    endpoint_registry_hash: str = ""
    scoring_version: str = SCORING_VERSION
    scoring_hash: str = ""
    calibration_version: str = CALIBRATION_VERSION
    calibration_id: str = ""
    calibration_hash: str = ""
    schedule_id: str = ""
    schedule_hash: str = ""
    task_generator_version: str = BATTERY_VERSION
    response_provider_id: str = ""
    response_provider_version: str = ""
    response_provider_config_hash: str = ""
    cognitive_agent_version: str = ""
    scenario_hash: str = ""
    oracle_spec_hash: str = ""
    primary_estimator_spec_hash: str = ""
    randomization_spec_hash: str = ""
    bootstrap_spec_hash: str = ""
    analysis_spec_hash: str = ""
    design_id: str = ""
    design_hash: str = ""
    rng_version: str = RNG_VERSION
    rng_version_hash: str = ""
    objective_runtime_version: str = OBJECTIVE_RUNTIME_VERSION
    provenance_version: str = PROVENANCE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def validate(self) -> list[str]:
        """Return list of missing required fields."""
        issues: list[str] = []
        if not self.endpoint_registry_hash:
            issues.append("missing endpoint_registry_hash")
        if not self.schedule_hash:
            issues.append("missing schedule_hash")
        if not self.response_provider_id:
            issues.append("missing response_provider_id")
        return issues

    def hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode()).hexdigest()


def create_objective_manifest(
    calibration_id: str = "",
    calibration_hash: str = "",
    schedule_id: str = "",
    schedule_hash: str = "",
    response_provider_id: str = "",
    response_provider_version: str = "",
    response_provider_config_hash: str = "",
    cognitive_agent_version: str = "",
    scenario_hash: str = "",
    oracle_spec_hash: str = "",
    primary_estimator_spec_hash: str = "",
    randomization_spec_hash: str = "",
    bootstrap_spec_hash: str = "",
    analysis_spec_hash: str = "",
    scoring_hash: str = "",
    design_id: str = "",
    design_hash: str = "",
) -> ObjectiveManifest:
    return ObjectiveManifest(
        endpoint_registry_hash=registry_hash(),
        scoring_hash=scoring_hash,
        calibration_id=calibration_id,
        calibration_hash=calibration_hash,
        schedule_id=schedule_id,
        schedule_hash=schedule_hash,
        response_provider_id=response_provider_id,
        response_provider_version=response_provider_version,
        response_provider_config_hash=response_provider_config_hash,
        cognitive_agent_version=cognitive_agent_version,
        scenario_hash=scenario_hash,
        oracle_spec_hash=oracle_spec_hash,
        primary_estimator_spec_hash=primary_estimator_spec_hash,
        randomization_spec_hash=randomization_spec_hash,
        bootstrap_spec_hash=bootstrap_spec_hash,
        analysis_spec_hash=analysis_spec_hash,
        design_id=design_id,
        design_hash=design_hash,
        rng_version_hash=rng_version_hash(),
    )


@dataclass
class CompletionSeal:
    """Cryptographic seal over objective session content."""
    session_id: str
    content_hash: str
    manifest_hash: str
    trial_count: int
    target_hash: str
    response_hash: str
    score_hash: str
    rating_hash: str
    leakage_audit_hash: str
    calibration_ref: str
    valid: bool = True
    seal_version: str = PROVENANCE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def seal_hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode()).hexdigest()


def create_completion_seal(
    session_result: ObjectiveSessionResult,
    manifest: ObjectiveManifest,
) -> CompletionSeal:
    """Create a cryptographic completion seal for an objective session."""
    targets = json.dumps(
        [t.target for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    responses = json.dumps(
        [t.response for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    scores = json.dumps(
        [{"composite": t.composite_error, "components": t.component_errors}
         for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    ratings = json.dumps(
        [{"confidence": t.confidence, "vividness": t.vividness, "effort": t.effort}
         for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    audit = json.dumps(
        [a.to_dict() for a in session_result.leakage_audit],
        sort_keys=True, separators=(",", ":"), default=str,
    )

    return CompletionSeal(
        session_id=session_result.session_id,
        content_hash=session_result.content_hash,
        manifest_hash=manifest.hash(),
        trial_count=len(session_result.trials),
        target_hash=hashlib.sha256(targets.encode()).hexdigest()[:16],
        response_hash=hashlib.sha256(responses.encode()).hexdigest()[:16],
        score_hash=hashlib.sha256(scores.encode()).hexdigest()[:16],
        rating_hash=hashlib.sha256(ratings.encode()).hexdigest()[:16],
        leakage_audit_hash=hashlib.sha256(audit.encode()).hexdigest()[:16],
        calibration_ref=manifest.calibration_id,
    )


def verify_seal(seal: CompletionSeal, session_result: ObjectiveSessionResult) -> list[str]:
    """Verify a completion seal against session data. Returns discrepancies."""
    issues: list[str] = []
    if seal.trial_count != len(session_result.trials):
        issues.append(f"trial_count mismatch: seal={seal.trial_count}, actual={len(session_result.trials)}")
    if seal.content_hash != session_result.content_hash:
        issues.append("content_hash mismatch")

    targets = json.dumps(
        [t.target for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    if hashlib.sha256(targets.encode()).hexdigest()[:16] != seal.target_hash:
        issues.append("target_hash mismatch")

    responses = json.dumps(
        [t.response for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    if hashlib.sha256(responses.encode()).hexdigest()[:16] != seal.response_hash:
        issues.append("response_hash mismatch")

    scores = json.dumps(
        [{"composite": t.composite_error, "components": t.component_errors}
         for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    if hashlib.sha256(scores.encode()).hexdigest()[:16] != seal.score_hash:
        issues.append("score_hash mismatch")

    ratings = json.dumps(
        [{"confidence": t.confidence, "vividness": t.vividness, "effort": t.effort}
         for t in session_result.trials],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    if hashlib.sha256(ratings.encode()).hexdigest()[:16] != seal.rating_hash:
        issues.append("rating_hash mismatch")

    audit = json.dumps(
        [a.to_dict() for a in session_result.leakage_audit],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    if hashlib.sha256(audit.encode()).hexdigest()[:16] != seal.leakage_audit_hash:
        issues.append("leakage_audit_hash mismatch")

    return issues


async def persist_manifest_and_seal(
    db,
    study_id: str,
    manifest: ObjectiveManifest,
    seal: CompletionSeal,
) -> dict[str, int]:
    """Persist manifest and seal to DB. Returns row IDs."""
    m_cursor = await db.execute(
        """INSERT INTO objective_manifests
           (study_id, manifest_hash, manifest_json, provenance_version)
           VALUES (?, ?, ?, ?)""",
        (study_id, manifest.hash(),
         json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":")),
         PROVENANCE_VERSION),
    )
    manifest_id = m_cursor.lastrowid

    s_cursor = await db.execute(
        """INSERT INTO objective_completion_seals
           (study_id, session_id, seal_hash, content_hash,
            manifest_hash, trial_count, target_hash,
            response_hash, score_hash, rating_hash,
            leakage_audit_hash, calibration_ref, valid,
            seal_version, seal_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (study_id, seal.session_id, seal.seal_hash(),
         seal.content_hash, seal.manifest_hash, seal.trial_count,
         seal.target_hash, seal.response_hash, seal.score_hash,
         seal.rating_hash, seal.leakage_audit_hash,
         seal.calibration_ref, int(seal.valid), seal.seal_version,
         json.dumps(seal.to_dict(), sort_keys=True, separators=(",", ":"))),
    )
    seal_id = s_cursor.lastrowid
    await db.commit()

    return {"manifest_id": manifest_id, "seal_id": seal_id}

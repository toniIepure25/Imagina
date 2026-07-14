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

"""Protocol-integrity audit for the CRT Stage 0F/0G and Stage 1 design.

The audit is intentionally conservative: prose, the YAML spec, and the simulator must agree on
trial arithmetic, the primary contrast, the Stage 0G design fields, and the human-study boundary
before Stage 1 can be registered. It is a design check, not evidence that the task works in humans.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

PROTOCOL_ID = "ANIMUS-CRT-v1"
EXPECTED_CELLS: tuple[str, ...] = (
    "active_intervene",
    "active_predict",
    "yoked_intervene",
    "yoked_predict",
)
EXPECTED_PRIMARY_CONTRAST = "yoked_predict_minus_yoked_intervene"
EXPECTED_SECONDARY_CONTRAST = "active_predict_minus_active_intervene"
DEFAULT_SESSION_CAP_MINUTES = 75.0
SETUP_MINUTES = 10.0
MINUTES_PER_TRIAL = 0.25


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_protocol_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "science" / "protocols" / "crt-v1.yaml"


@dataclass(frozen=True)
class DesignSpec:
    protocol_id: str
    version: str
    stage: str
    status: str
    trials_per_occasion: int
    observe_trials_per_occasion: int
    trials_per_cell_per_occasion: int
    cells: tuple[str, ...]
    occasions_days: tuple[int, ...]
    total_trials: int | None
    max_tests_per_trial: int
    session_cap_minutes: float
    primary_contrast: str
    secondary_contrast: str
    specificity_n: int | None = None
    dual_n: int | None = None
    dual_arms: tuple[str, ...] = ()
    main_n: int | None = None
    sesoi_d: float | None = None
    calibration_n: int | None = None
    primary_endpoint: str = ""
    model_space: tuple[str, ...] = ()
    confirmatory_models: tuple[str, ...] = ()
    exploratory_models: tuple[str, ...] = ()
    design_optimization_status: str = ""
    design_optimization_objective: str = ""
    design_optimization_method: str = ""
    adversarial_review_status: str = ""
    adversarial_bayesian_status: str = ""
    full_model_scope: str = ""
    policy_model_status: str = ""
    inference_backend: str = ""
    identifiability_status: str = ""
    source_audit_status: str = ""
    calibration_table_status: str = ""
    neural_extension_status: str = ""
    stage0h_status: str = ""
    stage0i_status: str = ""
    tests: tuple[str, ...] = ()
    likelihoods: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    zero_diagnosticity_tests: tuple[str, ...] = ()

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    @property
    def expected_trials_per_occasion(self) -> int:
        return self.n_cells * self.trials_per_cell_per_occasion + self.observe_trials_per_occasion

    @property
    def expected_total_trials(self) -> int:
        return self.expected_trials_per_occasion * len(self.occasions_days)

    @property
    def estimated_minutes_per_occasion(self) -> float:
        return SETUP_MINUTES + MINUTES_PER_TRIAL * self.trials_per_occasion

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "version": self.version,
            "stage": self.stage,
            "status": self.status,
            "trials_per_occasion": self.trials_per_occasion,
            "observe_trials_per_occasion": self.observe_trials_per_occasion,
            "trials_per_cell_per_occasion": self.trials_per_cell_per_occasion,
            "cells": list(self.cells),
            "occasions_days": list(self.occasions_days),
            "total_trials": self.total_trials,
            "expected_trials_per_occasion": self.expected_trials_per_occasion,
            "expected_total_trials": self.expected_total_trials,
            "max_tests_per_trial": self.max_tests_per_trial,
            "session_cap_minutes": self.session_cap_minutes,
            "estimated_minutes_per_occasion": round(self.estimated_minutes_per_occasion, 3),
            "primary_contrast": self.primary_contrast,
            "secondary_contrast": self.secondary_contrast,
            "specificity_n": self.specificity_n,
            "dual_n": self.dual_n,
            "dual_arms": list(self.dual_arms),
            "main_n": self.main_n,
            "sesoi_d": self.sesoi_d,
            "calibration_n": self.calibration_n,
            "primary_endpoint": self.primary_endpoint,
            "model_space": list(self.model_space),
            "confirmatory_models": list(self.confirmatory_models),
            "exploratory_models": list(self.exploratory_models),
            "design_optimization_status": self.design_optimization_status,
            "design_optimization_objective": self.design_optimization_objective,
            "design_optimization_method": self.design_optimization_method,
            "adversarial_review_status": self.adversarial_review_status,
            "adversarial_bayesian_status": self.adversarial_bayesian_status,
            "full_model_scope": self.full_model_scope,
            "policy_model_status": self.policy_model_status,
            "inference_backend": self.inference_backend,
            "identifiability_status": self.identifiability_status,
            "source_audit_status": self.source_audit_status,
            "calibration_table_status": self.calibration_table_status,
            "neural_extension_status": self.neural_extension_status,
            "stage0h_status": self.stage0h_status,
            "stage0i_status": self.stage0i_status,
            "tests": list(self.tests),
            "zero_diagnosticity_tests": list(self.zero_diagnosticity_tests),
        }


@dataclass(frozen=True)
class ProtocolAudit:
    spec: DesignSpec
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def decision(self) -> str:
        return "CRT_STAGE0F_PROTOCOL_PASS" if self.passed else "CRT_STAGE0F_PROTOCOL_REVIEW"

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL_ID,
            "analysis": "stage0f_protocol_integrity_audit",
            "spec": self.spec.as_dict(),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "decision": self.decision,
            "note": (
                "Design-integrity audit only. A PASS does not authorize human data collection, "
                "validate the task, or upgrade any claim."
            ),
        }


def _as_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _as_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def load_spec(path: Path | None = None) -> DesignSpec:
    path = path or default_protocol_path()
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("protocol YAML must be a mapping")
    design = document.get("design")
    if not isinstance(design, dict):
        raise ValueError("protocol YAML must contain a design mapping")

    cells = design.get("cells")
    if not isinstance(cells, list) or not all(isinstance(cell, str) for cell in cells):
        raise ValueError("design.cells must be a list of strings")
    occasions = design.get("occasions_days")
    if not isinstance(occasions, list) or not all(isinstance(day, int) for day in occasions):
        raise ValueError("design.occasions_days must be a list of integers")

    tests_doc = document.get("tests")
    tests: list[str] = []
    likelihoods: dict[str, dict[str, float]] = {}
    zero_tests: list[str] = []
    if isinstance(tests_doc, list):
        for entry in tests_doc:
            if not isinstance(entry, dict):
                continue
            test_id = str(entry.get("test_id", ""))
            if not test_id:
                continue
            tests.append(test_id)
            row = entry.get("likelihood_positive")
            if isinstance(row, dict):
                likelihoods[test_id] = {
                    str(source): float(probability) for source, probability in row.items()
                }
            if entry.get("zero_diagnosticity_trap") is True:
                zero_tests.append(test_id)

    specificity = document.get("specificity_substudy")
    dual = document.get("dual_substudy")
    specificity_n = None
    if isinstance(specificity, dict):
        raw_n = specificity.get("n")
        specificity_n = raw_n if isinstance(raw_n, int) else None
    dual_n = None
    dual_arms: tuple[str, ...] = ()
    if isinstance(dual, dict):
        raw_n = dual.get("n")
        dual_n = raw_n if isinstance(raw_n, int) else None
        raw_arms = dual.get("arms")
        if isinstance(raw_arms, list) and all(isinstance(arm, str) for arm in raw_arms):
            dual_arms = tuple(raw_arms)

    total_trials = design.get("total_trials")
    raw_main_n = design.get("main_n")
    main_n = raw_main_n if isinstance(raw_main_n, int) else None
    raw_sesoi = design.get("sesoi_d")
    sesoi_d = float(raw_sesoi) if isinstance(raw_sesoi, (int, float)) else None
    raw_calibration_n = design.get("calibration_n")
    calibration_n = raw_calibration_n if isinstance(raw_calibration_n, int) else None
    primary_endpoint = design.get("primary_endpoint")

    def _string_tuple(key: str) -> tuple[str, ...]:
        raw = design.get(key)
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            return ()
        return tuple(raw)

    return DesignSpec(
        protocol_id=_as_str(document.get("protocol_id"), "protocol_id"),
        version=_as_str(document.get("version"), "version"),
        stage=_as_str(document.get("stage"), "stage"),
        status=_as_str(document.get("status"), "status"),
        trials_per_occasion=_as_int(design.get("trials_per_occasion"), "design.trials_per_occasion"),
        observe_trials_per_occasion=_as_int(
            design.get("observe_trials_per_occasion"), "design.observe_trials_per_occasion"
        ),
        trials_per_cell_per_occasion=_as_int(
            design.get("trials_per_cell_per_occasion"), "design.trials_per_cell_per_occasion"
        ),
        cells=tuple(cells),
        occasions_days=tuple(occasions),
        total_trials=total_trials if isinstance(total_trials, int) else None,
        max_tests_per_trial=_as_int(design.get("max_tests_per_trial"), "design.max_tests_per_trial"),
        session_cap_minutes=float(design.get("session_cap_minutes", DEFAULT_SESSION_CAP_MINUTES)),
        primary_contrast=_as_str(design.get("primary_contrast"), "design.primary_contrast"),
        secondary_contrast=_as_str(design.get("secondary_contrast"), "design.secondary_contrast"),
        specificity_n=specificity_n,
        dual_n=dual_n,
        dual_arms=dual_arms,
        main_n=main_n,
        sesoi_d=sesoi_d,
        calibration_n=calibration_n,
        primary_endpoint=primary_endpoint if isinstance(primary_endpoint, str) else "",
        model_space=_string_tuple("model_space"),
        confirmatory_models=_string_tuple("confirmatory_models"),
        exploratory_models=_string_tuple("exploratory_models"),
        design_optimization_status=str(design.get("design_optimization_status", "")),
        design_optimization_objective=str(design.get("design_optimization_objective", "")),
        design_optimization_method=str(design.get("design_optimization_method", "")),
        adversarial_review_status=str(design.get("adversarial_review_status", "")),
        adversarial_bayesian_status=str(design.get("adversarial_bayesian_status", "")),
        full_model_scope=str(design.get("full_model_scope", "")),
        policy_model_status=str(design.get("policy_model_status", "")),
        inference_backend=str(design.get("inference_backend", "")),
        identifiability_status=str(design.get("identifiability_status", "")),
        source_audit_status=str(design.get("source_audit_status", "")),
        calibration_table_status=str(design.get("calibration_table_status", "")),
        neural_extension_status=str(design.get("neural_extension_status", "")),
        stage0h_status=str(design.get("stage0h_status", "")),
        stage0i_status=str(design.get("stage0i_status", "")),
        tests=tuple(tests),
        likelihoods=likelihoods,
        zero_diagnosticity_tests=tuple(zero_tests),
    )


def audit_spec(spec: DesignSpec) -> ProtocolAudit:
    errors: list[str] = []
    warnings: list[str] = []

    if spec.protocol_id != PROTOCOL_ID:
        errors.append(f"protocol_id must be {PROTOCOL_ID}")
    if spec.n_cells != 4:
        errors.append(f"design must have four cells, found {spec.n_cells}")
    if tuple(spec.cells) != EXPECTED_CELLS:
        errors.append(f"design.cells must be {list(EXPECTED_CELLS)}")
    if spec.expected_trials_per_occasion != spec.trials_per_occasion:
        errors.append(
            "trial arithmetic mismatch: "
            f"{spec.n_cells} cells x {spec.trials_per_cell_per_occasion} + "
            f"{spec.observe_trials_per_occasion} observe = "
            f"{spec.expected_trials_per_occasion}, but trials_per_occasion is "
            f"{spec.trials_per_occasion}"
        )
    if spec.total_trials is None:
        errors.append("design.total_trials must be declared explicitly")
    elif spec.total_trials != spec.expected_total_trials:
        errors.append(
            f"total_trials mismatch: declared {spec.total_trials}, expected {spec.expected_total_trials}"
        )
    if len(spec.occasions_days) != 2:
        errors.append("design must use exactly two occasions")
    if spec.observe_trials_per_occasion < 10:
        errors.append("observe_trials_per_occasion must be at least 10")
    if spec.max_tests_per_trial < 1:
        errors.append("max_tests_per_trial must be positive")
    if spec.max_tests_per_trial > len(spec.tests):
        errors.append("max_tests_per_trial cannot exceed the number of tests")
    if spec.estimated_minutes_per_occasion > spec.session_cap_minutes:
        errors.append(
            f"estimated session duration {spec.estimated_minutes_per_occasion:.1f} min exceeds "
            f"session_cap_minutes {spec.session_cap_minutes:.1f}"
        )
    if spec.primary_contrast != EXPECTED_PRIMARY_CONTRAST:
        errors.append(
            "primary_contrast must be the yoked prediction contrast "
            f"{EXPECTED_PRIMARY_CONTRAST!r}, found {spec.primary_contrast!r}"
        )
    if spec.secondary_contrast != EXPECTED_SECONDARY_CONTRAST:
        errors.append(
            "secondary_contrast must be labelled the active package contrast "
            f"{EXPECTED_SECONDARY_CONTRAST!r}, found {spec.secondary_contrast!r}"
        )
    if spec.specificity_n is None or spec.specificity_n <= 0:
        errors.append("specificity_substudy.n must be a positive integer")
    if spec.dual_n is None or spec.dual_n <= 0:
        errors.append("dual_substudy.n must be a positive integer")
    expected_dual_arms = (
        "active_predict_single",
        "active_predict_dual",
        "active_predict_dual_nondiagnostic",
    )
    if tuple(spec.dual_arms) != expected_dual_arms:
        errors.append(f"dual_substudy.arms must be {list(expected_dual_arms)}")

    expected_model_space = ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7")
    expected_confirmatory = ("M0", "M2", "M4", "M6", "M7")
    expected_exploratory = ("M1", "M3", "M5")
    if tuple(spec.model_space) != expected_model_space:
        errors.append(f"design.model_space must be {list(expected_model_space)}")
    if tuple(spec.confirmatory_models) != expected_confirmatory:
        errors.append(f"design.confirmatory_models must be {list(expected_confirmatory)}")
    if tuple(spec.exploratory_models) != expected_exploratory:
        errors.append(f"design.exploratory_models must be {list(expected_exploratory)}")
    if spec.design_optimization_status != "required_before_registration":
        errors.append("design_optimization_status must be required_before_registration")
    if spec.full_model_scope != "full_joint_source_monitoring_latent_state_not_policy_pomdp":
        errors.append("full_model_scope must declare the full joint latent-source scope")
    if not spec.stage0h_status.startswith("historical_computational_only"):
        errors.append("stage0h_status must be historical_computational_only_human_data_gated")
    if spec.stage0i_status != "computational_only_human_data_gated":
        errors.append("stage0i_status must be computational_only_human_data_gated")
    if "not_yet_reviewed" not in spec.adversarial_review_status:
        errors.append("adversarial_review_status must record that review is not complete")
    if "not_yet_reviewed" not in spec.adversarial_bayesian_status:
        errors.append("adversarial_bayesian_status must record that review is not complete")
    for field_name in (
        "design_optimization_method",
        "policy_model_status",
        "inference_backend",
        "identifiability_status",
        "source_audit_status",
        "calibration_table_status",
    ):
        if not getattr(spec, field_name):
            errors.append(f"design.{field_name} must be declared")

    if len(spec.tests) != 6:
        errors.append(f"design must retain six tests, found {len(spec.tests)}")
    for test_id, row in spec.likelihoods.items():
        if set(row) != {"seen", "imagined", "described", "new"}:
            errors.append(f"{test_id}: likelihood row must contain all four sources")
        for source, probability in row.items():
            if not 0.0 <= probability <= 1.0:
                errors.append(f"{test_id}/{source}: likelihood {probability} is outside [0, 1]")
    if spec.zero_diagnosticity_tests != ("fluency",):
        errors.append("the fluency test must be the only zero-diagnosticity trap")
    if "fluency" in spec.likelihoods:
        values = set(spec.likelihoods["fluency"].values())
        if len(values) != 1:
            errors.append("fluency likelihoods must be equal across sources")

    if spec.status != "registered":
        warnings.append("protocol is not registered; human collection remains blocked")
    if spec.stage.lower() not in {
        "0f",
        "stage0f",
        "0g",
        "stage0g",
        "0h",
        "stage0h",
        "0i",
        "stage0i",
        "1",
        "stage1",
    }:
        warnings.append(f"protocol stage {spec.stage!r} is not Stage 0F/0G/0H/0I/1")
    if spec.main_n is not None and spec.main_n < 360:
        errors.append("design.main_n must be at least 360 for the Stage 0G SESOI")
    if spec.sesoi_d is not None and not 0.05 <= spec.sesoi_d <= 0.50:
        errors.append("design.sesoi_d must be between 0.05 and 0.50")
    if spec.calibration_n is not None and spec.calibration_n < 40:
        errors.append("design.calibration_n must be at least 40")
    if spec.estimated_minutes_per_occasion > 60.0:
        warnings.append("estimated session duration exceeds 60 minutes")

    return ProtocolAudit(spec=spec, errors=tuple(errors), warnings=tuple(warnings))


def run_protocol_audit(path: Path | None = None) -> ProtocolAudit:
    return audit_spec(load_spec(path))


def require_protocol(path: Path | None = None) -> DesignSpec:
    audit = run_protocol_audit(path)
    if not audit.passed:
        raise ValueError("CRT protocol audit failed: " + "; ".join(audit.errors))
    return audit.spec


__all__ = [
    "DEFAULT_SESSION_CAP_MINUTES",
    "EXPECTED_CELLS",
    "EXPECTED_PRIMARY_CONTRAST",
    "EXPECTED_SECONDARY_CONTRAST",
    "DesignSpec",
    "ProtocolAudit",
    "audit_spec",
    "default_protocol_path",
    "load_spec",
    "repo_root",
    "require_protocol",
    "run_protocol_audit",
]

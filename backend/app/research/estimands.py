"""Formal causal estimands and identification assumptions.

Defines the primary and secondary causal estimands before any model fitting.
Every estimand specifies its contrast, population, sign interpretation,
and required identification assumptions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ESTIMAND_VERSION = "1.0"


class AnalysisPopulation(Enum):
    INTENTION_TO_TREAT = "intention_to_treat"
    PER_PROTOCOL = "per_protocol"
    SAFETY_ELIGIBLE = "safety_eligible"
    COMPLETE_CASE = "complete_case"
    MULTIPLE_IMPUTATION = "multiple_imputation"


class AssumptionStatus(Enum):
    STRUCTURALLY_ENFORCED = "structurally_enforced"
    EMPIRICALLY_CHECKABLE = "empirically_checkable"
    UNTESTABLE = "untestable"
    VIOLATED_IN_SIMULATION = "violated_in_simulation"


@dataclass(frozen=True)
class IdentificationAssumption:
    assumption_id: str
    name: str
    description: str
    status: AssumptionStatus
    verification_method: str

    def to_dict(self) -> dict[str, str]:
        return {
            "assumption_id": self.assumption_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "verification_method": self.verification_method,
        }


@dataclass(frozen=True)
class CausalEstimand:
    estimand_id: str
    version: str
    name: str
    description: str
    treatment: str
    control: str
    endpoint_id: str
    population: AnalysisPopulation
    sign_interpretation: str
    formal_expression: str
    contrast_type: str
    is_primary: bool
    is_confirmatory: bool
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimand_id": self.estimand_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "treatment": self.treatment,
            "control": self.control,
            "endpoint_id": self.endpoint_id,
            "population": self.population.value,
            "sign_interpretation": self.sign_interpretation,
            "formal_expression": self.formal_expression,
            "contrast_type": self.contrast_type,
            "is_primary": self.is_primary,
            "is_confirmatory": self.is_confirmatory,
            "assumptions": list(self.assumptions),
        }


# ---------------------------------------------------------------------------
# Identification assumptions
# ---------------------------------------------------------------------------

ASSUMPTIONS: dict[str, IdentificationAssumption] = {}


def _reg_assumption(a: IdentificationAssumption) -> IdentificationAssumption:
    ASSUMPTIONS[a.assumption_id] = a
    return a


_reg_assumption(IdentificationAssumption(
    "consistency", "Consistency",
    "The observed outcome under assignment to condition c equals the potential outcome Y(c).",
    AssumptionStatus.STRUCTURALLY_ENFORCED,
    "Enforced by deterministic runtime: same condition assignment produces same execution.",
))

_reg_assumption(IdentificationAssumption(
    "positivity", "Positivity",
    "Every participant has a nonzero probability of being assigned to every condition.",
    AssumptionStatus.STRUCTURALLY_ENFORCED,
    "Enforced by balanced Williams crossover: every participant receives all 3 conditions.",
))

_reg_assumption(IdentificationAssumption(
    "no_leakage", "No Condition-Information Leakage",
    "Participants and the outcome assessment are blinded to condition assignment.",
    AssumptionStatus.EMPIRICALLY_CHECKABLE,
    "Checked via perceived-contingency ratings across conditions.",
))

_reg_assumption(IdentificationAssumption(
    "correct_randomization", "Correct Randomization",
    "Sequence allocation follows the prespecified balanced Williams design.",
    AssumptionStatus.STRUCTURALLY_ENFORCED,
    "Enforced by deterministic allocator with balance verification.",
))

_reg_assumption(IdentificationAssumption(
    "no_carryover", "No Unmodeled Differential Carryover",
    "Effects of one condition do not persist into the next beyond what is modeled.",
    AssumptionStatus.EMPIRICALLY_CHECKABLE,
    "Checked via carryover indicator in sensitivity analysis and scenario simulation.",
))

_reg_assumption(IdentificationAssumption(
    "mar", "Missing At Random (MAR)",
    "Missingness depends on observed variables, not on unobserved potential outcomes.",
    AssumptionStatus.UNTESTABLE,
    "Sensitivity analysis compares complete-case vs. primary; informative dropout simulated.",
))

_reg_assumption(IdentificationAssumption(
    "stable_endpoint", "Stable Endpoint Definition",
    "The scoring function and endpoint weights do not change during the study.",
    AssumptionStatus.STRUCTURALLY_ENFORCED,
    "Enforced by frozen endpoint registry hash in manifest.",
))

_reg_assumption(IdentificationAssumption(
    "blinded_analysis", "Blinded Condition Labels for Analysis",
    "The analysis code does not have access to true condition labels during model specification.",
    AssumptionStatus.EMPIRICALLY_CHECKABLE,
    "Verified by preregistration and sealed analysis specification hash.",
))


# ---------------------------------------------------------------------------
# Estimand definitions
# ---------------------------------------------------------------------------

_ESTIMANDS: dict[str, CausalEstimand] = {}


def _reg_estimand(e: CausalEstimand) -> CausalEstimand:
    _ESTIMANDS[e.estimand_id] = e
    return e


PRIMARY_ESTIMAND = _reg_estimand(CausalEstimand(
    estimand_id="ate_adaptive_vs_yoked",
    version=ESTIMAND_VERSION,
    name="Average Treatment Effect: Adaptive vs. Yoked",
    description=(
        "Within-participant average treatment effect of adaptive versus yoked feedback "
        "on standardized objective imagery reconstruction error during post-baseline "
        "experimental trials."
    ),
    treatment="adaptive",
    control="yoked",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Negative effect = adaptive produces lower (better) reconstruction error than yoked",
    formal_expression="E[Y(adaptive) - Y(yoked)]",
    contrast_type="pairwise",
    is_primary=True,
    is_confirmatory=True,
    assumptions=["consistency", "positivity", "no_leakage", "correct_randomization",
                 "no_carryover", "mar", "stable_endpoint", "blinded_analysis"],
))

_reg_estimand(CausalEstimand(
    estimand_id="ate_adaptive_vs_fixed",
    version=ESTIMAND_VERSION,
    name="Average Treatment Effect: Adaptive vs. Fixed",
    description="Within-participant ATE of adaptive versus fixed feedback on primary endpoint.",
    treatment="adaptive",
    control="fixed",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Negative = adaptive better",
    formal_expression="E[Y(adaptive) - Y(fixed)]",
    contrast_type="pairwise",
    is_primary=False,
    is_confirmatory=True,
    assumptions=["consistency", "positivity", "correct_randomization", "no_carryover", "stable_endpoint"],
))

_reg_estimand(CausalEstimand(
    estimand_id="ate_fixed_vs_yoked",
    version=ESTIMAND_VERSION,
    name="Average Treatment Effect: Fixed vs. Yoked",
    description="Within-participant ATE of fixed versus yoked on primary endpoint.",
    treatment="fixed",
    control="yoked",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Negative = fixed better",
    formal_expression="E[Y(fixed) - Y(yoked)]",
    contrast_type="pairwise",
    is_primary=False,
    is_confirmatory=True,
    assumptions=["consistency", "positivity", "correct_randomization", "stable_endpoint"],
))

_reg_estimand(CausalEstimand(
    estimand_id="ate_adaptive_vs_average_control",
    version=ESTIMAND_VERSION,
    name="Adaptive vs. Average Control",
    description="Adaptive versus the average of fixed and yoked.",
    treatment="adaptive",
    control="average(fixed, yoked)",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Negative = adaptive better than average control",
    formal_expression="E[Y(adaptive) - 0.5*(Y(fixed) + Y(yoked))]",
    contrast_type="custom_contrast",
    is_primary=False,
    is_confirmatory=False,
    assumptions=["consistency", "positivity", "correct_randomization"],
))

_reg_estimand(CausalEstimand(
    estimand_id="condition_by_session",
    version=ESTIMAND_VERSION,
    name="Condition × Session Interaction",
    description="Interaction between condition and session progression on primary endpoint.",
    treatment="adaptive",
    control="yoked",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Negative interaction = adaptive improves more over sessions",
    formal_expression="E[(Y_adaptive_late - Y_adaptive_early) - (Y_yoked_late - Y_yoked_early)]",
    contrast_type="interaction",
    is_primary=False,
    is_confirmatory=False,
    assumptions=["consistency", "positivity", "correct_randomization", "no_carryover"],
))

_reg_estimand(CausalEstimand(
    estimand_id="objective_subjective_dissociation",
    version=ESTIMAND_VERSION,
    name="Objective vs. Subjective Change Dissociation",
    description="Whether objective precision change tracks subjective vividness change.",
    treatment="adaptive",
    control="yoked",
    endpoint_id="composite_reconstruction_error",
    population=AnalysisPopulation.INTENTION_TO_TREAT,
    sign_interpretation="Divergence = subjective changes without objective change",
    formal_expression="Corr(ΔY_objective, ΔY_subjective) by condition",
    contrast_type="descriptive",
    is_primary=False,
    is_confirmatory=False,
))


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

def get_estimand(estimand_id: str) -> CausalEstimand | None:
    return _ESTIMANDS.get(estimand_id)


def get_primary_estimand() -> CausalEstimand:
    return PRIMARY_ESTIMAND


def list_estimands() -> list[CausalEstimand]:
    return list(_ESTIMANDS.values())


def get_confirmatory_estimands() -> list[CausalEstimand]:
    return [e for e in _ESTIMANDS.values() if e.is_confirmatory]


def get_assumption(assumption_id: str) -> IdentificationAssumption | None:
    return ASSUMPTIONS.get(assumption_id)


def list_assumptions() -> list[IdentificationAssumption]:
    return list(ASSUMPTIONS.values())


def build_assumption_report() -> list[dict[str, Any]]:
    """Build a structured assumption report with status for each."""
    report: list[dict[str, Any]] = []
    for a in ASSUMPTIONS.values():
        report.append({
            **a.to_dict(),
            "used_by": [e.estimand_id for e in _ESTIMANDS.values() if a.assumption_id in e.assumptions],
        })
    return report


def estimand_hash() -> str:
    data = {eid: e.to_dict() for eid, e in sorted(_ESTIMANDS.items())}
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()

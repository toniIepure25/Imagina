"""Research-mode simulation campaign with checkpointing and reporting.

Runs at least 1000 replicates per core scenario, stores per-batch
and combined summaries, and reports calibrated operating characteristics.

Fails closed: campaigns with zero valid replicates report metrics as None
and campaign_valid=False. No numerical Type-I error, power, or coverage
is reported when there are zero valid replicates.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_DROPOUT,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PLACEBO_EXPECTANCY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_SMALL_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
    SCENARIO_WEAK_RELIABILITY,
    AgentScenario,
)
from app.research.design_simulation import SimulationResult, run_simulation

CAMPAIGN_VERSION = "3.0"

CORE_SCENARIOS: dict[str, AgentScenario] = {
    "strict_null": SCENARIO_STRICT_NULL,
    "small_adaptive": SCENARIO_SMALL_ADAPTIVE,
    "medium_adaptive": SCENARIO_MEDIUM_ADAPTIVE,
    "subjective_only": SCENARIO_SUBJECTIVE_ONLY,
    "practice_only": SCENARIO_PRACTICE_ONLY,
    "placebo_only": SCENARIO_PLACEBO_EXPECTANCY,
    "perceptual_only": SCENARIO_PERCEPTUAL_ONLY,
    "carryover": SCENARIO_CARRYOVER,
    "differential_dropout": SCENARIO_DROPOUT,
    "weak_reliability": SCENARIO_WEAK_RELIABILITY,
}

DEFAULT_RESEARCH_REPLICATES = 1000
DEFAULT_BATCH_SIZE = 100


@dataclass
class BatchSummary:
    scenario_id: str
    batch_index: int
    batch_seed: int
    n_iterations: int
    n_valid: int
    n_invalid: int
    campaign_valid: bool
    oracle_effect: float
    oracle_se: float
    type_i_error: float | None
    power: float | None
    bias: float | None
    rmse: float | None
    coverage: float | None
    convergence_rate: float
    fallback_rate: float
    valid_inference_rate: float
    negative_control_fp_rate: float | None
    interval_width: float | None
    elapsed_s: float

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ScenarioSummary:
    scenario_id: str
    total_replicates: int
    n_valid_replicates: int
    n_invalid_replicates: int
    n_batches: int
    campaign_valid: bool
    invalid_reason: str
    oracle_effect: float
    oracle_se: float
    type_i_error: float | None
    type_i_se: float | None
    power: float | None
    power_se: float | None
    bias: float | None
    bias_se: float | None
    rmse: float | None
    coverage: float | None
    coverage_se: float | None
    interval_width: float | None
    convergence_rate: float
    fallback_rate: float
    valid_inference_rate: float
    negative_control_fp_rate: float | None
    elapsed_s: float
    calibration_pass: bool = False
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class CampaignResult:
    campaign_id: str
    version: str = CAMPAIGN_VERSION
    total_replicates: int = 0
    total_scenarios: int = 0
    scenario_summaries: dict[str, ScenarioSummary] = field(default_factory=dict)
    batch_summaries: list[BatchSummary] = field(default_factory=list)
    overall_pass: bool = False
    elapsed_s: float = 0.0
    gate_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "version": self.version,
            "total_replicates": self.total_replicates,
            "total_scenarios": self.total_scenarios,
            "overall_pass": self.overall_pass,
            "elapsed_s": round(self.elapsed_s, 2),
            "gate_issues": self.gate_issues,
            "scenario_summaries": {k: v.to_dict() for k, v in self.scenario_summaries.items()},
            "n_batch_summaries": len(self.batch_summaries),
        }


def _safe_combine_proportions(
    values: list[float | None],
    counts: list[int],
) -> tuple[float | None, float | None]:
    valid_pairs = [(v, c) for v, c in zip(values, counts) if v is not None and c > 0]
    if not valid_pairs:
        return None, None
    total = sum(c for _, c in valid_pairs)
    if total == 0:
        return None, None
    weighted = sum(v * c for v, c in valid_pairs) / total
    se = math.sqrt(weighted * (1 - weighted) / total) if total > 1 else 0.0
    return weighted, se


def _safe_combine_means(
    means: list[float | None],
    counts: list[int],
) -> tuple[float | None, float | None]:
    valid_pairs = [(m, c) for m, c in zip(means, counts) if m is not None and c > 0]
    if not valid_pairs:
        return None, None
    total = sum(c for _, c in valid_pairs)
    if total == 0:
        return None, None
    weighted = sum(m * c for m, c in valid_pairs) / total
    if total > 1 and len(valid_pairs) > 1:
        var = sum(c * (m - weighted) ** 2 for m, c in valid_pairs) / total
        se = math.sqrt(var / len(valid_pairs))
    else:
        se = 0.0
    return weighted, se


def run_scenario_campaign(
    scenario_id: str,
    scenario: AgentScenario,
    total_replicates: int = DEFAULT_RESEARCH_REPLICATES,
    batch_size: int = DEFAULT_BATCH_SIZE,
    n_participants: int = 18,
    base_seed: int = 42,
    checkpoint_callback: Any = None,
) -> ScenarioSummary:
    """Run a full campaign for one scenario with batched execution."""
    n_batches = max(1, (total_replicates + batch_size - 1) // batch_size)
    batch_results: list[BatchSummary] = []
    start = time.time()

    for bi in range(n_batches):
        batch_n = min(batch_size, total_replicates - bi * batch_size)
        if batch_n <= 0:
            break

        batch_seed = base_seed + bi * 100000
        batch_start = time.time()

        result = run_simulation(
            scenario,
            n_iterations=batch_n,
            n_participants=n_participants,
            base_seed=batch_seed,
            mode="research",
        )

        batch_elapsed = time.time() - batch_start

        bs = BatchSummary(
            scenario_id=scenario_id,
            batch_index=bi,
            batch_seed=batch_seed,
            n_iterations=batch_n,
            n_valid=result.n_valid_replicates,
            n_invalid=result.n_invalid_replicates,
            campaign_valid=result.campaign_valid,
            oracle_effect=result.oracle_effect,
            oracle_se=result.oracle_se,
            type_i_error=result.type_i_error,
            power=result.power,
            bias=result.bias,
            rmse=result.rmse,
            coverage=result.coverage,
            convergence_rate=result.convergence_rate,
            fallback_rate=result.fallback_rate,
            valid_inference_rate=result.valid_inference_rate,
            negative_control_fp_rate=result.negative_control_fp_rate,
            interval_width=result.interval_width,
            elapsed_s=batch_elapsed,
        )
        batch_results.append(bs)

        if checkpoint_callback:
            checkpoint_callback(bs)

    total_elapsed = time.time() - start
    counts = [b.n_iterations for b in batch_results]
    valid_counts = [b.n_valid for b in batch_results]
    total_valid = sum(valid_counts)
    total_invalid = sum(b.n_invalid for b in batch_results)
    total_n = sum(counts)

    type_i, type_i_se = _safe_combine_proportions(
        [b.type_i_error for b in batch_results], valid_counts)
    power_val, power_se = _safe_combine_proportions(
        [b.power for b in batch_results], valid_counts)
    coverage_val, coverage_se = _safe_combine_proportions(
        [b.coverage for b in batch_results], valid_counts)
    convergence, _ = _safe_combine_proportions(
        [b.convergence_rate for b in batch_results], counts)
    fallback, _ = _safe_combine_proportions(
        [b.fallback_rate for b in batch_results], counts)
    valid_inf, _ = _safe_combine_proportions(
        [b.valid_inference_rate for b in batch_results], counts)
    nc_fp, _ = _safe_combine_proportions(
        [b.negative_control_fp_rate for b in batch_results], counts)

    bias_val, bias_se = _safe_combine_means(
        [b.bias for b in batch_results], valid_counts)
    rmse_val, _ = _safe_combine_means(
        [b.rmse for b in batch_results], valid_counts)
    iw_val, _ = _safe_combine_means(
        [b.interval_width for b in batch_results], valid_counts)

    oracle_effect = batch_results[0].oracle_effect if batch_results else 0.0
    oracle_se = batch_results[0].oracle_se if batch_results else 0.0

    issues: list[str] = []
    is_null = scenario.adaptive_precision_effect == 0 and scenario.adaptive_control_effect == 0

    if total_valid == 0:
        issues.append("zero_valid_replicates")
    elif valid_inf is not None and valid_inf < 0.50:
        issues.append(f"valid_inference_too_low_{valid_inf:.4f}")

    if is_null and type_i is not None:
        mc_tol = 2.576 * math.sqrt(0.05 * 0.95 / total_valid) if total_valid > 0 else 0.1
        if type_i > 0.05 + mc_tol:
            issues.append(f"type_i_inflated_{type_i:.4f}")

    if coverage_val is not None and coverage_val == 0.0:
        issues.append(f"coverage_zero_{coverage_val:.4f}")
    elif coverage_val is not None and coverage_val < 0.85:
        issues.append(f"coverage_too_low_{coverage_val:.4f}")

    if fallback is not None and fallback > 0.50:
        issues.append(f"fallback_dominates_{fallback:.4f}")

    invalid_reason = "; ".join(issues) if issues else ""
    campaign_valid = len(issues) == 0

    def _r(v: float | None, n: int = 4) -> float | None:
        return round(v, n) if v is not None else None

    return ScenarioSummary(
        scenario_id=scenario_id,
        total_replicates=total_n,
        n_valid_replicates=total_valid,
        n_invalid_replicates=total_invalid,
        n_batches=len(batch_results),
        campaign_valid=campaign_valid,
        invalid_reason=invalid_reason,
        oracle_effect=oracle_effect,
        oracle_se=oracle_se,
        type_i_error=_r(type_i),
        type_i_se=_r(type_i_se),
        power=_r(power_val),
        power_se=_r(power_se),
        bias=_r(bias_val, 6),
        bias_se=_r(bias_se, 6),
        rmse=_r(rmse_val, 6),
        coverage=_r(coverage_val),
        coverage_se=_r(coverage_se),
        interval_width=_r(iw_val, 6),
        convergence_rate=_r(convergence) or 0.0,
        fallback_rate=_r(fallback) or 0.0,
        valid_inference_rate=_r(valid_inf) or 0.0,
        negative_control_fp_rate=_r(nc_fp),
        elapsed_s=total_elapsed,
        calibration_pass=campaign_valid,
        issues=issues,
    )


def run_full_campaign(
    total_replicates: int = DEFAULT_RESEARCH_REPLICATES,
    batch_size: int = DEFAULT_BATCH_SIZE,
    n_participants: int = 18,
    base_seed: int = 42,
    scenarios: dict[str, AgentScenario] | None = None,
    checkpoint_callback: Any = None,
) -> CampaignResult:
    """Run campaigns across all core scenarios."""
    if scenarios is None:
        scenarios = CORE_SCENARIOS

    campaign_id = hashlib.sha256(
        json.dumps({
            "replicates": total_replicates,
            "participants": n_participants,
            "seed": base_seed,
            "version": CAMPAIGN_VERSION,
            "scenarios": sorted(scenarios.keys()),
        }, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

    result = CampaignResult(campaign_id=campaign_id)
    start = time.time()

    for sid, scenario in scenarios.items():
        ss = run_scenario_campaign(
            sid, scenario,
            total_replicates=total_replicates,
            batch_size=batch_size,
            n_participants=n_participants,
            base_seed=base_seed,
            checkpoint_callback=checkpoint_callback,
        )
        result.scenario_summaries[sid] = ss
        result.total_replicates += ss.total_replicates
        result.total_scenarios += 1

        if not ss.campaign_valid:
            result.gate_issues.append(f"{sid}: {ss.invalid_reason}")

    result.elapsed_s = time.time() - start
    result.overall_pass = len(result.gate_issues) == 0

    return result


def campaign_hash(result: CampaignResult) -> str:
    data = json.dumps({
        "campaign_id": result.campaign_id,
        "version": result.version,
        "total_replicates": result.total_replicates,
        "overall_pass": result.overall_pass,
        "gate_issues": result.gate_issues,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()

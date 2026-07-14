"""Research-mode simulation campaign with checkpointing and reporting.

Runs at least 1000 replicates per core scenario, stores per-batch
and combined summaries, and reports calibrated operating characteristics.
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
    AgentScenario,
)
from app.research.design_simulation import run_simulation

CAMPAIGN_VERSION = "1.0"

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
}

DEFAULT_RESEARCH_REPLICATES = 1000
DEFAULT_BATCH_SIZE = 100


@dataclass
class BatchSummary:
    scenario_id: str
    batch_index: int
    batch_seed: int
    n_iterations: int
    oracle_effect: float
    oracle_se: float
    type_i_error: float
    power: float
    bias: float
    rmse: float
    coverage: float
    convergence_rate: float
    fallback_rate: float
    valid_inference_rate: float
    negative_control_fp_rate: float
    interval_width: float
    elapsed_s: float

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ScenarioSummary:
    scenario_id: str
    total_replicates: int
    n_batches: int
    oracle_effect: float
    oracle_se: float
    type_i_error: float
    type_i_se: float
    power: float
    power_se: float
    bias: float
    bias_se: float
    rmse: float
    coverage: float
    coverage_se: float
    interval_width: float
    convergence_rate: float
    fallback_rate: float
    valid_inference_rate: float
    negative_control_fp_rate: float
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


def _combine_proportions(values: list[float], counts: list[int]) -> tuple[float, float]:
    """Weighted average of proportions with binomial SE."""
    total = sum(counts)
    if total == 0:
        return 0.0, 0.0
    weighted = sum(v * c for v, c in zip(values, counts)) / total
    se = math.sqrt(weighted * (1 - weighted) / total) if total > 1 else 0.0
    return weighted, se


def _combine_means(means: list[float], counts: list[int]) -> tuple[float, float]:
    """Weighted average of means with SE."""
    total = sum(counts)
    if total == 0:
        return 0.0, 0.0
    weighted = sum(m * c for m, c in zip(means, counts)) / total
    if total > 1 and len(means) > 1:
        var = sum(c * (m - weighted) ** 2 for m, c in zip(means, counts)) / total
        se = math.sqrt(var / len(means))
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

    type_i, type_i_se = _combine_proportions([b.type_i_error for b in batch_results], counts)
    power_val, power_se = _combine_proportions([b.power for b in batch_results], counts)
    coverage, coverage_se = _combine_proportions([b.coverage for b in batch_results], counts)
    convergence, _ = _combine_proportions([b.convergence_rate for b in batch_results], counts)
    fallback, _ = _combine_proportions([b.fallback_rate for b in batch_results], counts)
    valid_inf, _ = _combine_proportions([b.valid_inference_rate for b in batch_results], counts)
    nc_fp, _ = _combine_proportions([b.negative_control_fp_rate for b in batch_results], counts)

    bias_val, bias_se = _combine_means([b.bias for b in batch_results], counts)
    rmse_val, _ = _combine_means([b.rmse for b in batch_results], counts)
    iw_val, _ = _combine_means([b.interval_width for b in batch_results], counts)

    oracle_effect = batch_results[0].oracle_effect if batch_results else 0.0
    oracle_se = batch_results[0].oracle_se if batch_results else 0.0

    issues: list[str] = []
    is_null = scenario.adaptive_precision_effect == 0 and scenario.adaptive_control_effect == 0
    if is_null:
        mc_tol = 2.576 * math.sqrt(0.05 * 0.95 / sum(counts)) if sum(counts) > 0 else 0.1
        if type_i > 0.05 + mc_tol:
            issues.append(f"Type-I error inflated: {type_i:.4f} > 0.05 + {mc_tol:.4f}")
    if coverage < 0.90:
        issues.append(f"Coverage too low: {coverage:.4f}")
    if fallback > 0.50:
        issues.append(f"Fallback dominates: {fallback:.4f}")
    if valid_inf < 0.50:
        issues.append(f"Valid inference too low: {valid_inf:.4f}")

    return ScenarioSummary(
        scenario_id=scenario_id,
        total_replicates=sum(counts),
        n_batches=len(batch_results),
        oracle_effect=oracle_effect,
        oracle_se=oracle_se,
        type_i_error=round(type_i, 4),
        type_i_se=round(type_i_se, 4),
        power=round(power_val, 4),
        power_se=round(power_se, 4),
        bias=round(bias_val, 6),
        bias_se=round(bias_se, 6),
        rmse=round(rmse_val, 6),
        coverage=round(coverage, 4),
        coverage_se=round(coverage_se, 4),
        interval_width=round(iw_val, 6),
        convergence_rate=round(convergence, 4),
        fallback_rate=round(fallback, 4),
        valid_inference_rate=round(valid_inf, 4),
        negative_control_fp_rate=round(nc_fp, 4),
        elapsed_s=total_elapsed,
        calibration_pass=len(issues) == 0,
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
    """Run the full research-mode simulation campaign across all core scenarios."""
    if scenarios is None:
        scenarios = CORE_SCENARIOS

    campaign_id = hashlib.sha256(
        json.dumps({
            "replicates": total_replicates,
            "batch_size": batch_size,
            "n_participants": n_participants,
            "seed": base_seed,
            "scenarios": sorted(scenarios.keys()),
            "version": CAMPAIGN_VERSION,
        }, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

    result = CampaignResult(campaign_id=f"campaign-{campaign_id}")
    start = time.time()

    for sid, scenario in scenarios.items():
        scenario_seed = base_seed + hash(sid) % 100000
        ss = run_scenario_campaign(
            sid, scenario,
            total_replicates=total_replicates,
            batch_size=batch_size,
            n_participants=n_participants,
            base_seed=scenario_seed,
            checkpoint_callback=checkpoint_callback,
        )
        result.scenario_summaries[sid] = ss
        result.total_replicates += ss.total_replicates

    result.total_scenarios = len(result.scenario_summaries)
    result.elapsed_s = time.time() - start

    for sid, ss in result.scenario_summaries.items():
        if not ss.calibration_pass:
            for issue in ss.issues:
                result.gate_issues.append(f"[{sid}] {issue}")

    result.overall_pass = len(result.gate_issues) == 0
    return result


def campaign_hash(result: CampaignResult) -> str:
    data = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()

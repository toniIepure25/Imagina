"""Simulation-based operating-characteristic validation.

Repeatedly generates complete studies, runs confirmatory analysis, and
estimates power, Type-I error, bias, RMSE, and CI coverage across scenarios.
Uses observed-scale oracle for truth, all 4 task families, and applied dropout.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Any

from app.research.causal_oracle import DEFAULT_TARGETS, compute_oracle_effect
from app.research.cognitive_agent import (
    SCENARIOS,
    AgentScenario,
    generate_population,
    generate_trial_response,
    should_dropout,
)
from app.research.rng_registry import derive_seed
from app.research.statistics.confirmatory import run_primary_analysis

SIMULATION_VERSION = "3.0"

MIN_VALID_INFERENCE_RATE = 0.50
MAX_FALLBACK_RATE = 0.50

SIMULATION_MODES = {
    "unit": {"iterations": 15, "description": "Structural invariants only"},
    "ci": {"iterations": 150, "description": "Broad regression thresholds"},
    "research": {"iterations": 1000, "description": "Checkpointed and resumable"},
    "publication_candidate": {"iterations": 5000, "description": "Configurable 5000+"},
}

FAST_ITERATIONS = 15
CI_ITERATIONS = 150
RESEARCH_ITERATIONS = 1000

WILLIAMS_SEQUENCES = [
    ["adaptive", "fixed", "yoked"],
    ["fixed", "yoked", "adaptive"],
    ["yoked", "adaptive", "fixed"],
    ["yoked", "fixed", "adaptive"],
    ["adaptive", "yoked", "fixed"],
    ["fixed", "adaptive", "yoked"],
]

TASK_FAMILIES = ["feature_reconstruction", "imagery_manipulation", "delayed_imagery", "perceptual_control"]
DELAYS = [0.0, 0.0, 3.0, 0.0]


@dataclass
class SimulationResult:
    scenario_id: str
    n_iterations: int
    n_participants: int
    sessions_per_participant: int
    trials_per_task: int
    power: float | None
    power_se: float | None
    type_i_error: float | None
    type_i_se: float | None
    mean_estimate: float | None
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
    oracle_effect: float
    oracle_se: float
    seed_set: list[int]
    scenario_version: str
    campaign_valid: bool = True
    invalid_reason: str = ""
    n_valid_replicates: int = 0
    n_invalid_replicates: int = 0
    bootstrap_valid_rate: float | None = None
    mode: str = "unit"
    simulation_version: str = SIMULATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


FROZEN_STRIDE = 1000


@dataclass
class SimulationAccumulator:
    valid_count: int = 0
    invalid_count: int = 0
    rejections: int = 0
    nc_rejections: int = 0
    nc_analyses: int = 0
    converged_count: int = 0
    fallback_count: int = 0
    estimate_sum: float = 0.0
    estimate_sum_sq: float = 0.0
    squared_error_sum: float = 0.0
    ci_covers_count: int = 0
    ci_width_sum: float = 0.0
    seeds: list[int] = field(default_factory=list)
    oracle_truth: float = 0.0
    oracle_se: float = 0.0
    scenario_id: str = ""
    scenario_version: str = ""

    def merge(self, other: SimulationAccumulator) -> SimulationAccumulator:
        return SimulationAccumulator(
            valid_count=self.valid_count + other.valid_count,
            invalid_count=self.invalid_count + other.invalid_count,
            rejections=self.rejections + other.rejections,
            nc_rejections=self.nc_rejections + other.nc_rejections,
            nc_analyses=self.nc_analyses + other.nc_analyses,
            converged_count=self.converged_count + other.converged_count,
            fallback_count=self.fallback_count + other.fallback_count,
            estimate_sum=self.estimate_sum + other.estimate_sum,
            estimate_sum_sq=self.estimate_sum_sq + other.estimate_sum_sq,
            squared_error_sum=self.squared_error_sum + other.squared_error_sum,
            ci_covers_count=self.ci_covers_count + other.ci_covers_count,
            ci_width_sum=self.ci_width_sum + other.ci_width_sum,
            seeds=self.seeds + other.seeds,
            oracle_truth=self.oracle_truth,
            oracle_se=self.oracle_se,
            scenario_id=self.scenario_id,
            scenario_version=self.scenario_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationAccumulator:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    def finalize(
        self,
        n_iterations: int,
        n_participants: int = 18,
        sessions_per_participant: int = 3,
        trials_per_task: int = 5,
        alpha: float = 0.05,
        mode: str = "unit",
    ) -> SimulationResult:
        n = n_iterations
        vc = self.valid_count
        n_invalid = n - vc
        valid_rate = vc / n if n > 0 else 0.0
        fallback_rate_val = self.fallback_count / n if n > 0 else 0.0
        convergence_rate_val = self.converged_count / n if n > 0 else 0.0

        is_null = self.oracle_truth == 0.0

        invalid_reasons: list[str] = []
        if vc == 0:
            invalid_reasons.append("zero_valid_replicates")
        if valid_rate < MIN_VALID_INFERENCE_RATE:
            invalid_reasons.append(f"valid_rate_{valid_rate:.2f}_below_{MIN_VALID_INFERENCE_RATE}")

        campaign_valid = len(invalid_reasons) == 0

        if vc == 0:
            return SimulationResult(
                scenario_id=self.scenario_id, n_iterations=n,
                n_participants=n_participants,
                sessions_per_participant=sessions_per_participant,
                trials_per_task=trials_per_task,
                power=None, power_se=None, type_i_error=None, type_i_se=None,
                mean_estimate=None, bias=None, bias_se=None, rmse=None,
                coverage=None, coverage_se=None, interval_width=None,
                convergence_rate=convergence_rate_val,
                fallback_rate=fallback_rate_val,
                valid_inference_rate=0.0,
                negative_control_fp_rate=None,
                oracle_effect=round(self.oracle_truth, 6),
                oracle_se=round(self.oracle_se, 6),
                seed_set=self.seeds, scenario_version=self.scenario_version,
                campaign_valid=False, invalid_reason="; ".join(invalid_reasons),
                n_valid_replicates=0, n_invalid_replicates=n_invalid,
                mode=mode,
            )

        rejection_rate = self.rejections / vc
        mean_est = self.estimate_sum / vc
        bias_val = mean_est - self.oracle_truth
        rmse_val = math.sqrt(self.squared_error_sum / vc)
        coverage_val = self.ci_covers_count / vc if vc > 0 else 0.0
        avg_width = self.ci_width_sum / vc if vc > 0 else 0.0

        power_val = rejection_rate if not is_null else None
        type_i_val = rejection_rate if is_null else None
        rate_se = math.sqrt(rejection_rate * (1 - rejection_rate) / vc) if vc > 1 else 0.0
        cov_se = math.sqrt(coverage_val * (1 - coverage_val) / vc) if vc > 1 else 0.0

        bias_se_val = 0.0
        if vc > 1:
            est_var = (self.estimate_sum_sq - self.estimate_sum ** 2 / vc) / (vc - 1)
            est_var = max(0.0, est_var)
            bias_se_val = math.sqrt(est_var / vc)

        nc_fp = self.nc_rejections / self.nc_analyses if self.nc_analyses > 0 else None

        return SimulationResult(
            scenario_id=self.scenario_id, n_iterations=n,
            n_participants=n_participants,
            sessions_per_participant=sessions_per_participant,
            trials_per_task=trials_per_task,
            power=round(power_val, 4) if power_val is not None else None,
            power_se=round(rate_se, 4) if not is_null else None,
            type_i_error=round(type_i_val, 4) if type_i_val is not None else None,
            type_i_se=round(rate_se, 4) if is_null else None,
            mean_estimate=round(mean_est, 6),
            bias=round(bias_val, 6), bias_se=round(bias_se_val, 6),
            rmse=round(rmse_val, 6),
            coverage=round(coverage_val, 4), coverage_se=round(cov_se, 4),
            interval_width=round(avg_width, 6),
            convergence_rate=round(convergence_rate_val, 4),
            fallback_rate=round(fallback_rate_val, 4),
            valid_inference_rate=round(valid_rate, 4),
            negative_control_fp_rate=round(nc_fp, 4) if nc_fp is not None else None,
            oracle_effect=round(self.oracle_truth, 6),
            oracle_se=round(self.oracle_se, 6),
            seed_set=self.seeds, scenario_version=self.scenario_version,
            campaign_valid=campaign_valid,
            invalid_reason="; ".join(invalid_reasons) if invalid_reasons else "",
            n_valid_replicates=vc,
            n_invalid_replicates=n_invalid,
            mode=mode,
        )


@dataclass
class BatchSimulationEvidence:
    accumulator: SimulationAccumulator
    replicate_start: int
    replicate_count: int


def run_simulation_batch(
    scenario: AgentScenario,
    replicate_start: int,
    replicate_count: int,
    n_participants: int = 18,
    base_seed: int = 42,
    mode: str = "unit",
    oracle_truth: float = 0.0,
    alpha: float = 0.05,
    sessions_per_participant: int = 3,
    trials_per_task: int = 5,
    abort_callback: Any = None,
) -> BatchSimulationEvidence:
    acc = SimulationAccumulator(
        oracle_truth=oracle_truth,
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.version,
    )

    for r in range(replicate_start, replicate_start + replicate_count):
        if abort_callback is not None:
            abort_callback()

        sim_seed = base_seed + r * FROZEN_STRIDE
        acc.seeds.append(sim_seed)

        imagery_data, nc_data = _generate_study_data(
            scenario, n_participants, sessions_per_participant, trials_per_task, sim_seed,
        )

        result = run_primary_analysis(imagery_data, alpha=alpha)

        if result.converged and not result.is_fallback:
            acc.converged_count += 1
        if result.is_fallback:
            acc.fallback_count += 1

        if result.inference_valid:
            acc.valid_count += 1
            est = result.effect_estimate
            acc.estimate_sum += est
            acc.estimate_sum_sq += est * est
            acc.squared_error_sum += (est - oracle_truth) ** 2
            if result.p_value <= alpha:
                acc.rejections += 1
            covered = result.ci_lower <= oracle_truth <= result.ci_upper
            if covered:
                acc.ci_covers_count += 1
            acc.ci_width_sum += result.ci_upper - result.ci_lower
        else:
            acc.invalid_count += 1

        if nc_data:
            nc_result = run_primary_analysis(nc_data, alpha=alpha)
            acc.nc_analyses += 1
            if nc_result.inference_valid and nc_result.p_value <= alpha:
                acc.nc_rejections += 1

    return BatchSimulationEvidence(
        accumulator=acc,
        replicate_start=replicate_start,
        replicate_count=replicate_count,
    )


@dataclass
class DesignRecommendation:
    n_participants: int
    sessions_per_participant: int
    trials_per_task: int
    expected_analyzable: int
    estimated_power: float
    type_i_error: float
    assumptions: list[str]
    scenario_version: str
    simulation_seed_set: list[int]
    code_sha: str

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def _generate_study_data(
    scenario: AgentScenario,
    n_participants: int,
    sessions_per_participant: int,
    trials_per_task: int,
    sim_seed: int,
) -> tuple[list[dict], list[dict]]:
    """Generate one complete study with all task families, dropout, etc."""
    pop = generate_population(n_participants, seed=sim_seed, scenario=scenario)
    imagery_data: list[dict] = []
    nc_data: list[dict] = []

    for ai, agent in enumerate(pop):
        seq_idx = ai % len(WILLIAMS_SEQUENCES)
        seq = WILLIAMS_SEQUENCES[seq_idx]
        dropout_rng = random.Random(derive_seed(sim_seed, "dropout", participant_id=agent.participant_id))
        dropped = False

        for si in range(min(sessions_per_participant, len(seq))):
            if dropped:
                break
            if si > 0 and should_dropout(agent, si, scenario, dropout_rng):
                dropped = True
                break

            cond = seq[si]
            prev_cond = seq[si - 1] if si > 0 else None

            for tf_idx, task_family in enumerate(TASK_FAMILIES):
                is_pc = task_family == "perceptual_control"
                delay = DELAYS[tf_idx]
                target_pool = DEFAULT_TARGETS

                for ti in range(trials_per_task):
                    target = target_pool[ti % len(target_pool)]
                    trial_seed = derive_seed(sim_seed, "simulation",
                                             participant_id=agent.participant_id,
                                             session_index=si, trial_index=tf_idx * trials_per_task + ti)
                    r = generate_trial_response(
                        agent, target, target, cond, si, ti,
                        scenario, is_pc, trial_seed,
                        delay_s=delay,
                        prev_condition=prev_cond,
                    )
                    r["period"] = si
                    r["sequence"] = seq_idx
                    r["baseline_precision"] = agent.baseline_imagery_precision
                    r["task_family"] = task_family
                    r["carryover_indicator"] = prev_cond if prev_cond else "none"

                    if is_pc:
                        nc_data.append(r)
                    else:
                        imagery_data.append(r)

    return imagery_data, nc_data


def run_simulation(
    scenario: AgentScenario,
    n_iterations: int | None = None,
    n_participants: int = 18,
    sessions_per_participant: int = 3,
    trials_per_task: int = 5,
    base_seed: int = 42,
    alpha: float = 0.05,
    mode: str = "unit",
) -> SimulationResult:
    """Run Monte Carlo simulation for operating characteristics.

    Fails closed: campaigns with zero valid replicates report metrics as None,
    not 0.0. Campaign validity is explicitly flagged.
    """
    if n_iterations is None:
        n_iterations = SIMULATION_MODES.get(mode, SIMULATION_MODES["unit"])["iterations"]

    oracle = compute_oracle_effect(scenario, n_agents=100, seed=base_seed + 999999)
    oracle_truth = oracle.effect

    rejections = 0
    nc_rejections = 0
    nc_analyses = 0
    valid_estimates: list[float] = []
    ci_covers: list[bool] = []
    ci_widths: list[float] = []
    converged_count = 0
    fallback_count = 0
    valid_count = 0
    seed_set: list[int] = []

    for iteration in range(n_iterations):
        sim_seed = base_seed + iteration * 1000
        seed_set.append(sim_seed)

        imagery_data, nc_data = _generate_study_data(
            scenario, n_participants, sessions_per_participant, trials_per_task, sim_seed,
        )

        result = run_primary_analysis(imagery_data, alpha=alpha)

        is_valid = result.inference_valid
        if result.converged and not result.is_fallback:
            converged_count += 1
        if is_valid:
            valid_count += 1
            valid_estimates.append(result.effect_estimate)
            if result.p_value <= alpha:
                rejections += 1
            covered = result.ci_lower <= oracle_truth <= result.ci_upper
            ci_covers.append(covered)
            ci_widths.append(result.ci_upper - result.ci_lower)
        if result.is_fallback:
            fallback_count += 1

        if nc_data:
            nc_result = run_primary_analysis(nc_data, alpha=alpha)
            nc_analyses += 1
            if nc_result.inference_valid and nc_result.p_value <= alpha:
                nc_rejections += 1

    n = n_iterations
    n_invalid = n - valid_count
    valid_rate = valid_count / n if n > 0 else 0.0
    fallback_rate_val = fallback_count / n if n > 0 else 0.0
    convergence_rate_val = converged_count / n if n > 0 else 0.0

    is_null = all(
        getattr(scenario, attr) == 0
        for attr in ["adaptive_precision_effect", "adaptive_control_effect",
                      "adaptive_stability_effect"]
    )

    invalid_reasons: list[str] = []
    if valid_count == 0:
        invalid_reasons.append("zero_valid_replicates")
    if valid_rate < MIN_VALID_INFERENCE_RATE:
        invalid_reasons.append(f"valid_rate_{valid_rate:.2f}_below_{MIN_VALID_INFERENCE_RATE}")
    if is_null and abs(oracle_truth) > 1e-8:
        invalid_reasons.append(f"strict_null_oracle_nonzero_{oracle_truth}")

    campaign_valid = len(invalid_reasons) == 0

    if valid_count == 0:
        return SimulationResult(
            scenario_id=scenario.scenario_id, n_iterations=n,
            n_participants=n_participants,
            sessions_per_participant=sessions_per_participant,
            trials_per_task=trials_per_task,
            power=None, power_se=None, type_i_error=None, type_i_se=None,
            mean_estimate=None, bias=None, bias_se=None, rmse=None,
            coverage=None, coverage_se=None, interval_width=None,
            convergence_rate=convergence_rate_val,
            fallback_rate=fallback_rate_val,
            valid_inference_rate=0.0,
            negative_control_fp_rate=None,
            oracle_effect=round(oracle_truth, 6),
            oracle_se=round(oracle.effect_se, 6),
            seed_set=seed_set, scenario_version=scenario.version,
            campaign_valid=False, invalid_reason="; ".join(invalid_reasons),
            n_valid_replicates=0, n_invalid_replicates=n_invalid,
            mode=mode,
        )

    rejection_rate = rejections / valid_count
    mean_est = sum(valid_estimates) / valid_count
    bias_val = mean_est - oracle_truth
    mse = sum((e - oracle_truth) ** 2 for e in valid_estimates) / valid_count
    rmse = math.sqrt(mse)
    coverage_val = sum(1 for c in ci_covers if c) / len(ci_covers) if ci_covers else 0.0
    avg_width = sum(ci_widths) / len(ci_widths) if ci_widths else 0.0

    power_val = rejection_rate if not is_null else None
    type_i_val = rejection_rate if is_null else None
    rate_se = math.sqrt(rejection_rate * (1 - rejection_rate) / valid_count) if valid_count > 1 else 0.0
    cov_n = len(ci_covers) if ci_covers else 1
    cov_se = math.sqrt(coverage_val * (1 - coverage_val) / cov_n) if cov_n > 1 else 0.0

    bias_se_val = 0.0
    if valid_count > 1:
        est_var = sum((e - mean_est) ** 2 for e in valid_estimates) / (valid_count - 1)
        bias_se_val = math.sqrt(est_var / valid_count)

    nc_fp = nc_rejections / nc_analyses if nc_analyses > 0 else None

    return SimulationResult(
        scenario_id=scenario.scenario_id, n_iterations=n,
        n_participants=n_participants,
        sessions_per_participant=sessions_per_participant,
        trials_per_task=trials_per_task,
        power=round(power_val, 4) if power_val is not None else None,
        power_se=round(rate_se, 4) if not is_null else None,
        type_i_error=round(type_i_val, 4) if type_i_val is not None else None,
        type_i_se=round(rate_se, 4) if is_null else None,
        mean_estimate=round(mean_est, 6),
        bias=round(bias_val, 6), bias_se=round(bias_se_val, 6),
        rmse=round(rmse, 6),
        coverage=round(coverage_val, 4), coverage_se=round(cov_se, 4),
        interval_width=round(avg_width, 6),
        convergence_rate=round(convergence_rate_val, 4),
        fallback_rate=round(fallback_rate_val, 4),
        valid_inference_rate=round(valid_rate, 4),
        negative_control_fp_rate=round(nc_fp, 4) if nc_fp is not None else None,
        oracle_effect=round(oracle_truth, 6),
        oracle_se=round(oracle.effect_se, 6),
        seed_set=seed_set, scenario_version=scenario.version,
        campaign_valid=campaign_valid,
        invalid_reason="; ".join(invalid_reasons) if invalid_reasons else "",
        n_valid_replicates=valid_count,
        n_invalid_replicates=n_invalid,
        mode=mode,
    )


def run_scenario_grid(
    n_iterations: int = FAST_ITERATIONS,
    n_participants: int = 18,
    base_seed: int = 42,
) -> dict[str, SimulationResult]:
    """Run simulation across the full scenario grid."""
    results: dict[str, SimulationResult] = {}
    for scenario_id, scenario in SCENARIOS.items():
        results[scenario_id] = run_simulation(
            scenario, n_iterations=n_iterations,
            n_participants=n_participants, base_seed=base_seed,
        )
    return results


def generate_design_recommendation(
    sim_results: dict[str, SimulationResult],
    code_sha: str = "synthetic",
) -> DesignRecommendation:
    """Produce a design recommendation based on simulation results."""
    null_result = sim_results.get("strict_null")
    medium_result = sim_results.get("medium_adaptive")

    if medium_result:
        ref = medium_result
    else:
        ref = next(iter(sim_results.values()))

    return DesignRecommendation(
        n_participants=ref.n_participants,
        sessions_per_participant=ref.sessions_per_participant,
        trials_per_task=ref.trials_per_task,
        expected_analyzable=ref.n_participants * ref.sessions_per_participant * ref.trials_per_task,
        estimated_power=ref.power if ref.power > 0 else 0.5,
        type_i_error=null_result.type_i_error if null_result else 0.05,
        assumptions=[
            "Within-participant crossover with balanced Williams sequences",
            "Synthetic cognitive agent model v1.0",
            f"Monte Carlo SE reflects {ref.n_iterations} iterations",
        ],
        scenario_version=ref.scenario_version,
        simulation_seed_set=ref.seed_set[:5],
        code_sha=code_sha,
    )


def simulation_hash(scenario_id: str, n_iterations: int, seed: int) -> str:
    data = json.dumps(
        {"scenario": scenario_id, "n_iterations": n_iterations,
         "seed": seed, "version": SIMULATION_VERSION},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(data.encode()).hexdigest()

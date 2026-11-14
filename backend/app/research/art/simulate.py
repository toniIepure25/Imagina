"""Deterministic Stage 0 simulator for Active Reality Testing (ART)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import mean
from typing import Sequence

from app.research.art.design import DEFAULT_CARDS, card_costs, source_schedule
from app.research.art.metrics import (
    DecisionRecord,
    QueryRecord,
    TrialRecord,
    information_resolution,
    summarize,
)
from app.research.art.model import (
    CARD_IDS,
    CONTEXT,
    DEFAULT_PRIOR,
    AgentParams,
    effective_likelihoods,
    entropy,
    expected_information_gain,
    expected_random_eig,
    greedy_eig,
    posterior_from_evidence,
    softmax,
)

POLICIES = ("eig", "fixed", "heuristic", "random")


@dataclass(frozen=True)
class SimulationConfig:
    n_participants: int = 60
    n_trials: int = 80
    seed: int = 20261029
    max_queries: int = 2
    cost_multiplier: float = 1.0
    cost_levels: tuple[float, ...] = (1.0,)
    beta_mean: float = 2.0
    beta_sd: float = 0.35
    lam_mean: float = 0.25
    lam_sd: float = 0.10
    tau_mean: float = -0.20
    tau_sd: float = 0.10
    d_mean: float = 1.0
    d_sd: float = 0.08
    lapse: float = 0.02
    confidence_noise: float = 0.05

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.max_queries <= 0:
            raise ValueError("max_queries must be positive")
        if self.cost_multiplier < 0:
            raise ValueError("cost_multiplier must be non-negative")
        if not self.cost_levels or any(level < 0 for level in self.cost_levels):
            raise ValueError("cost_levels must be a non-empty sequence of non-negative values")
        if not 0.0 <= self.lapse <= 1.0:
            raise ValueError("lapse must be in [0, 1]")


@dataclass
class ParticipantResult:
    true_params: AgentParams
    trials: list[TrialRecord]
    decisions: list[DecisionRecord]
    schedule: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class RecoveredParams:
    beta: float
    lam: float
    tau: float


def _clamp_params(params: AgentParams) -> AgentParams:
    return AgentParams(
        beta=max(0.05, params.beta),
        lam=max(0.0, params.lam),
        tau=params.tau,
        d=max(0.3, params.d),
        lapse=min(1.0, max(0.0, params.lapse)),
        confidence_noise=max(0.0, params.confidence_noise),
    )


def _weighted_index(weights: Sequence[float], rng: random.Random) -> int:
    total = sum(weights)
    if total <= 0:
        return rng.randrange(len(weights))
    threshold = rng.random() * total
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if threshold <= cumulative:
            return index
    return len(weights) - 1


def _policy_utilities(
    eig: Sequence[float],
    costs: Sequence[float],
    beta: float,
    lam: float,
) -> list[float]:
    maximum = max(eig) if eig else 0.0
    scale = maximum if maximum > 1e-12 else 1.0
    return [beta * (gain / scale - lam * cost) for gain, cost in zip(eig, costs)]


def _decision_index(
    eig: Sequence[float],
    costs: Sequence[float],
    params: AgentParams,
    rng: random.Random,
) -> int:
    utilities = _policy_utilities(eig, costs, params.beta, params.lam)
    options = utilities + [params.tau]
    if params.lapse > 0 and rng.random() < params.lapse:
        return rng.randrange(len(options))
    return _weighted_index(softmax(options), rng)


def _choose_source(
    posterior: Sequence[float],
    params: AgentParams,
    rng: random.Random,
) -> int:
    if params.lapse > 0 and rng.random() < params.lapse:
        return rng.randrange(len(posterior))
    return max(range(len(posterior)), key=posterior.__getitem__)


def _simulate_trial(
    true_source: int,
    params: AgentParams,
    likelihoods: Sequence[Sequence[float]],
    rng: random.Random,
    max_queries: int,
    costs: Sequence[float],
    policy: str = "eig",
) -> tuple[TrialRecord, list[DecisionRecord]]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    prior = DEFAULT_PRIOR
    posterior = prior
    queries: list[QueryRecord] = []
    decisions: list[DecisionRecord] = []
    cards = CARD_IDS
    available = list(range(len(cards)))

    for step in range(max_queries):
        if not available:
            break
        eig = tuple(
            expected_information_gain(posterior, card_index, likelihoods)
            for card_index in available
        )
        aligned_costs = tuple(costs[card_index] for card_index in available)
        if policy == "eig":
            index = _decision_index(eig, aligned_costs, params, rng)
            if index == len(available):
                decisions.append(
                    DecisionRecord(tuple(available), eig, aligned_costs, -1)
                )
                break
            position = index
            card_index = available[position]
        elif policy == "fixed":
            position = 0
            card_index = available[position]
        elif policy == "heuristic":
            if step >= 2:
                decisions.append(
                    DecisionRecord(tuple(available), eig, aligned_costs, -1)
                )
                break
            card_index = CONTEXT if CONTEXT in available else available[0]
            position = available.index(card_index)
        else:
            position = rng.randrange(len(available))
            card_index = available[position]

        probability = likelihoods[card_index][true_source]
        evidence = rng.random() < probability
        max_eig = max(eig)
        queries.append(
            QueryRecord(
                card=card_index,
                evidence=evidence,
                eig=eig[position],
                cost=costs[card_index],
                max_eig=max_eig,
            )
        )
        decisions.append(
            DecisionRecord(tuple(available), eig, aligned_costs, position)
        )
        posterior = posterior_from_evidence(posterior, ((card_index, evidence),), likelihoods)
        available.pop(position)

    choice = _choose_source(posterior, params, rng)
    confidence = min(1.0, max(0.05, posterior[choice]))
    if params.confidence_noise > 0:
        confidence = min(
            1.0,
            max(0.05, confidence + rng.gauss(0.0, params.confidence_noise)),
        )
    prior_entropy = entropy(prior)
    final_entropy = entropy(posterior)
    human_eig = sum(query.eig for query in queries)
    n_queries = len(queries)
    if n_queries > 0:
        greedy = greedy_eig(prior, n_queries, range(len(cards)), likelihoods)
        random_eig = expected_random_eig(prior, n_queries, range(len(cards)), likelihoods)
        denominator = greedy - random_eig
        if denominator > 1e-9:
            arte_raw = (human_eig - random_eig) / denominator
            arte = max(0.0, min(1.0, arte_raw))
        else:
            arte_raw = None
            arte = None
    else:
        greedy = random_eig = 0.0
        arte_raw = None
        arte = None

    return (
        TrialRecord(
            true_source=true_source,
            choice=choice,
            confidence=confidence,
            correct=choice == true_source,
            queries=tuple(queries),
            prior_entropy=prior_entropy,
            final_entropy=final_entropy,
            human_eig=human_eig,
            greedy_eig=greedy,
            random_eig=random_eig,
            arte=arte,
            arte_raw=arte_raw,
            evidence_resolution=information_resolution(prior, posterior),
        ),
        decisions,
    )


def simulate_participant(
    config: SimulationConfig,
    params: AgentParams,
    seed: int,
    policy: str = "eig",
) -> ParticipantResult:
    params = _clamp_params(params)
    rng = random.Random(seed)
    schedule = source_schedule(config.n_trials, seed + 17)
    likelihoods = effective_likelihoods(params.d)
    trials: list[TrialRecord] = []
    decisions: list[DecisionRecord] = []
    for true_source in schedule:
        costs = card_costs(
            DEFAULT_CARDS,
            config.cost_multiplier * rng.choice(config.cost_levels),
        )
        trial, trial_decisions = _simulate_trial(
            true_source=true_source,
            params=params,
            likelihoods=likelihoods,
            rng=rng,
            max_queries=config.max_queries,
            costs=costs,
            policy=policy,
        )
        trials.append(trial)
        decisions.extend(trial_decisions)
    return ParticipantResult(
        true_params=params,
        trials=trials,
        decisions=decisions,
        schedule=schedule,
    )


def _sample_params(config: SimulationConfig, rng: random.Random) -> AgentParams:
    return _clamp_params(
        AgentParams(
            beta=max(0.1, rng.gauss(config.beta_mean, config.beta_sd)),
            lam=max(0.0, rng.gauss(config.lam_mean, config.lam_sd)),
            tau=rng.gauss(config.tau_mean, config.tau_sd),
            d=max(0.4, rng.gauss(config.d_mean, config.d_sd)),
            lapse=config.lapse,
            confidence_noise=config.confidence_noise,
        )
    )


def _aggregate(results: Sequence[ParticipantResult]) -> dict[str, object]:
    summaries = [summarize(result.trials) for result in results]
    all_trials = [trial for result in results for trial in result.trials]
    card_counts = {card: 0 for card in CARD_IDS}
    source_counts = {
        "seen": 0,
        "imagined": 0,
        "described": 0,
        "new": 0,
    }
    for trial in all_trials:
        source_counts[
            ("seen", "imagined", "described", "new")[trial.true_source]
        ] += 1
        for query in trial.queries:
            card_counts[CARD_IDS[query.card]] += 1

    arte_values = [summary.mean_arte for summary in summaries if summary.mean_arte is not None]
    sampling_values = [
        summary.mean_sampling_quality
        for summary in summaries
        if summary.mean_sampling_quality is not None
    ]
    return {
        "n_participants": len(results),
        "n_trials": len(all_trials),
        "mean_accuracy": round(mean(summary.accuracy for summary in summaries), 6),
        "mean_brier_score": round(mean(summary.brier_score for summary in summaries), 6),
        "mean_expected_calibration_error": round(
            mean(summary.expected_calibration_error for summary in summaries), 6
        ),
        "mean_queries": round(mean(summary.mean_queries for summary in summaries), 6),
        "mean_arte": None if not arte_values else round(mean(arte_values), 6),
        "mean_sampling_quality": (
            None if not sampling_values else round(mean(sampling_values), 6)
        ),
        "mean_evidence_resolution": round(
            mean(summary.mean_evidence_resolution for summary in summaries), 6
        ),
        "mean_d_prime_seen_imagined": round(
            mean(summary.d_prime_seen_imagined for summary in summaries), 6
        ),
        "insufficient_query_trials": sum(summary.insufficient_queries for summary in summaries),
        "card_counts": card_counts,
        "source_counts": source_counts,
        "example": summarize(results[0].trials).as_dict() if results else None,
    }


def run_simulation(config: SimulationConfig, policy: str = "eig") -> dict[str, object]:
    results: list[ParticipantResult] = []
    for participant in range(config.n_participants):
        rng = random.Random(config.seed + participant)
        params = _sample_params(config, rng)
        results.append(simulate_participant(config, params, config.seed + participant, policy))
    measurement = _aggregate(results)
    decision = "PASS"
    if measurement["mean_arte"] is None or float(measurement["mean_arte"]) < 0.30:
        decision = "REVIEW"
    if float(measurement["mean_accuracy"]) < 0.35:
        decision = "REVIEW"
    return {
        "protocol": "ANIMUS-ART-v1",
        "design": policy,
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "max_queries": config.max_queries,
            "cost_multiplier": config.cost_multiplier,
            "beta_mean": config.beta_mean,
            "lam_mean": config.lam_mean,
            "tau_mean": config.tau_mean,
            "d_mean": config.d_mean,
            "lapse": config.lapse,
        },
        "decision": f"ART_STAGE0_SIMULATION_{decision}",
        "measurement": measurement,
        "note": (
            "Simulation-only design gate. A PASS means the EIG agent is above chance and its "
            "query choices are efficient under the stated model; it is not human evidence."
        ),
    }


def _logsumexp(values: Sequence[float]) -> float:
    maximum = max(values)
    return maximum + math.log(sum(math.exp(value - maximum) for value in values))


def _policy_log_likelihood(
    decisions: Sequence[DecisionRecord],
    params: RecoveredParams,
) -> float:
    total = 0.0
    for decision in decisions:
        utilities = _policy_utilities(
            decision.eig,
            decision.costs,
            params.beta,
            params.lam,
        )
        utilities.append(params.tau)
        chosen_index = decision.chosen if decision.chosen >= 0 else len(decision.eig)
        total += utilities[chosen_index] - _logsumexp(utilities)
    return total


def fit_policy(decisions: Sequence[DecisionRecord]) -> RecoveredParams:
    """Grid-search the policy parameters conditional on the known EIG feature matrix."""
    if not decisions:
        return RecoveredParams(beta=0.0, lam=0.0, tau=0.0)
    best = RecoveredParams(beta=1.0, lam=0.0, tau=0.0)
    best_ll = -math.inf
    for beta in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0):
        for lam in (0.0, 0.1, 0.2, 0.3, 0.5, 0.7):
            for tau in (-1.0, -0.6, -0.3, -0.1, 0.1, 0.3):
                candidate = RecoveredParams(beta=beta, lam=lam, tau=tau)
                ll = _policy_log_likelihood(decisions, candidate)
                if ll > best_ll:
                    best_ll = ll
                    best = candidate
    return best


def run_recovery(config: SimulationConfig | None = None) -> dict[str, object]:
    config = config or SimulationConfig(
        n_participants=20,
        n_trials=60,
        seed=20261029,
        cost_levels=(0.5, 1.0, 2.0),
    )
    true_values: list[RecoveredParams] = []
    estimated_values: list[RecoveredParams] = []
    for participant in range(config.n_participants):
        rng = random.Random(config.seed + participant)
        params = _sample_params(config, rng)
        result = simulate_participant(config, params, config.seed + participant)
        estimated = fit_policy(result.decisions)
        true_values.append(RecoveredParams(params.beta, params.lam, params.tau))
        estimated_values.append(estimated)

    def errors(name: str) -> list[float]:
        return [
            getattr(estimated, name) - getattr(true, name)
            for true, estimated in zip(true_values, estimated_values)
        ]

    beta_errors = errors("beta")
    lam_errors = errors("lam")
    tau_errors = errors("tau")
    beta_bias = mean(beta_errors)
    beta_rmse = math.sqrt(mean(error**2 for error in beta_errors))
    lam_bias = mean(lam_errors)
    lam_rmse = math.sqrt(mean(error**2 for error in lam_errors))
    tau_bias = mean(tau_errors)
    tau_rmse = math.sqrt(mean(error**2 for error in tau_errors))
    passed = (
        abs(beta_bias) <= 0.30
        and beta_rmse <= 0.80
        and abs(lam_bias) <= 0.12
        and lam_rmse <= 0.25
        and abs(tau_bias) <= 0.30
        and tau_rmse <= 0.60
    )
    return {
        "protocol": "ANIMUS-ART-v1",
        "analysis": "conditional_logit_grid_recovery",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
        },
        "recovery": {
            "beta": {
                "mean_true": round(mean(value.beta for value in true_values), 6),
                "mean_estimated": round(mean(value.beta for value in estimated_values), 6),
                "bias": round(beta_bias, 6),
                "rmse": round(beta_rmse, 6),
            },
            "lam": {
                "mean_true": round(mean(value.lam for value in true_values), 6),
                "mean_estimated": round(mean(value.lam for value in estimated_values), 6),
                "bias": round(lam_bias, 6),
                "rmse": round(lam_rmse, 6),
            },
            "tau": {
                "mean_true": round(mean(value.tau for value in true_values), 6),
                "mean_estimated": round(mean(value.tau for value in estimated_values), 6),
                "bias": round(tau_bias, 6),
                "rmse": round(tau_rmse, 6),
            },
        },
        "decision": "ART_STAGE0_RECOVERY_PASS" if passed else "ART_STAGE0_RECOVERY_REVIEW",
        "note": (
            "Policy-parameter recovery conditional on the known EIG feature matrix. It does not "
            "recover the full hierarchical measurement model or validate the task in humans."
        ),
    }


def compare_policies(config: SimulationConfig | None = None) -> dict[str, object]:
    config = config or SimulationConfig(n_participants=20, n_trials=60, seed=20261029)
    reports = {}
    for policy in POLICIES:
        results = []
        for participant in range(config.n_participants):
            rng = random.Random(config.seed + participant)
            params = _sample_params(config, rng)
            results.append(simulate_participant(config, params, config.seed + participant, policy))
        reports[policy] = _aggregate(results)
    eig_arte = reports["eig"]["mean_arte"]
    comparison_pass = (
        eig_arte is not None
        and float(eig_arte) >= 0.30
        and all(
            reports[policy]["mean_arte"] is None
            or float(eig_arte) > float(reports[policy]["mean_arte"])
            for policy in ("fixed", "heuristic", "random")
        )
    )
    return {
        "protocol": "ANIMUS-ART-v1",
        "analysis": "policy_comparison",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
        },
        "policies": reports,
        "decision": "ART_STAGE0_POLICY_PASS" if comparison_pass else "ART_STAGE0_POLICY_REVIEW",
        "note": (
            "Descriptive comparison of simulated agents. The EIG agent is expected to show the "
            "highest sampling efficiency; this is not a model-comparison result from human data."
        ),
    }


def check_simulation() -> dict[str, object]:
    report = run_simulation(SimulationConfig(n_participants=12, n_trials=30, seed=7))
    if report["decision"] != "ART_STAGE0_SIMULATION_PASS":
        raise AssertionError(f"ART simulation gate failed: {report['measurement']}")
    return report


def check_recovery() -> dict[str, object]:
    report = run_recovery(
        SimulationConfig(
            n_participants=12,
            n_trials=60,
            seed=7,
            cost_levels=(0.5, 1.0, 2.0),
        )
    )
    if report["decision"] != "ART_STAGE0_RECOVERY_PASS":
        raise AssertionError(f"ART recovery gate failed: {report['recovery']}")
    return report


def check_policy_comparison() -> dict[str, object]:
    report = compare_policies(SimulationConfig(n_participants=12, n_trials=30, seed=7))
    if report["decision"] != "ART_STAGE0_POLICY_PASS":
        raise AssertionError(f"ART policy comparison failed: {report['policies']}")
    return report


__all__ = [
    "POLICIES",
    "ParticipantResult",
    "RecoveredParams",
    "SimulationConfig",
    "check_policy_comparison",
    "check_recovery",
    "check_simulation",
    "compare_policies",
    "fit_policy",
    "run_recovery",
    "run_simulation",
    "simulate_participant",
]

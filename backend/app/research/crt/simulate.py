"""Deterministic Stage 0 simulator for Counterfactual Reality Testing (CRT)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import mean
from typing import Sequence

from app.research.crt.design import (
    CONDITIONS,
    DEFAULT_TESTS,
    source_schedule,
    test_agency_values,
    test_complexities,
    test_costs,
)
from app.research.crt.metrics import (
    DecisionRecord,
    TestRecord,
    TrialRecord,
    information_resolution,
    summarize,
)
from app.research.crt.model import (
    ALL_TESTS,
    DEFAULT_PRIOR,
    FLUENCY,
    INTEND,
    AgentParams,
    apply_prediction_bias,
    choose_source_probabilities,
    counterfactual_discrimination,
    eig,
    entropy,
    expected_random_eig,
    expected_random_meta_eig,
    greedy_eig,
    greedy_meta_eig,
    meta_eig,
    outcome_likelihood,
    posterior_from_outcome,
    posterior_from_prediction_outcome,
    prediction_likelihood,
    softmax,
)

POLICIES = ("meta_eig", "eig", "positive", "fixed", "heuristic", "random", "agency", "mixture")
_PREDICT_CONDITIONS = ("active_predict", "yoked_predict")
_ACTIVE_CONDITIONS = ("active_intervene", "active_predict")


@dataclass(frozen=True)
class SimulationConfig:
    n_participants: int = 60
    n_trials: int = 120
    seed: int = 20261029
    max_tests: int = 2
    cost_multiplier: float = 1.0
    cost_levels: tuple[float, ...] = (1.0,)
    beta_mean: float = 2.0
    beta_sd: float = 0.35
    lam_mean: float = 0.25
    lam_sd: float = 0.10
    gamma_mean: float = 0.20
    gamma_sd: float = 0.08
    tau_mean: float = -0.20
    tau_sd: float = 0.10
    d_mean: float = 1.0
    d_sd: float = 0.08
    pi_mean: float = 1.20
    pi_sd: float = 0.20
    b_pi_mean: float = 0.30
    b_pi_sd: float = 0.10
    mix_mean: float = 1.00
    mix_sd: float = 0.00
    guess_mean: float = 0.00
    guess_sd: float = 0.00
    bias_mean: float = 0.00
    bias_sd: float = 0.00
    confidence_noise: float = 0.05
    lapse: float = 0.0
    alpha: float = 0.5

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.max_tests <= 0:
            raise ValueError("max_tests must be positive")
        if self.cost_multiplier < 0:
            raise ValueError("cost_multiplier must be non-negative")
        if not self.cost_levels or any(level < 0 for level in self.cost_levels):
            raise ValueError("cost_levels must be a non-empty sequence of non-negative values")


@dataclass
class ParticipantResult:
    true_params: AgentParams
    trials: list[TrialRecord]
    decisions: list[DecisionRecord]
    scripts: list[tuple[int, ...]] = field(default_factory=list)
    schedule: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class RecoveredParams:
    beta: float
    lam: float
    gamma: float
    tau: float
    mix: float
    pi: float
    b_pi: float


def _clamp_params(params: AgentParams) -> AgentParams:
    return AgentParams(
        beta=max(0.05, params.beta),
        lam=max(0.0, params.lam),
        gamma=max(0.0, params.gamma),
        tau=params.tau,
        d=max(0.3, params.d),
        pi=max(0.0, params.pi),
        b_pi=max(0.0, params.b_pi),
        guess=min(1.0, max(0.0, params.guess)),
        bias=min(1.0, max(0.0, params.bias)),
        lapse=min(1.0, max(0.0, params.lapse)),
        confidence_noise=max(0.0, params.confidence_noise),
        mix=min(1.0, max(0.0, params.mix)),
        alpha=min(2.0, max(0.0, params.alpha)),
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


def _positive_value(posterior: Sequence[float], test: int, d: float) -> float:
    predictor = max(range(len(posterior)), key=lambda source: posterior[source])
    probability = outcome_likelihood(test, predictor, d)
    return max(probability, 1.0 - probability)


def _policy_utilities(
    posterior: Sequence[float],
    available: Sequence[int],
    params: AgentParams,
    costs: Sequence[float],
    complexities: Sequence[float],
    agency_values: Sequence[float],
) -> tuple[list[float], list[float], list[float], list[float], list[float], list[float]]:
    meta_values = [meta_eig(posterior, test, params.pi, params.d) for test in available]
    eig_values = [eig(posterior, test, params.d) for test in available]
    positive_values = [_positive_value(posterior, test, params.d) for test in available]
    max_meta = max(meta_values) if meta_values else 0.0
    max_eig = max(eig_values) if eig_values else 0.0
    max_positive = max(positive_values) if positive_values else 0.0
    max_agency = max(agency_values) if agency_values else 0.0
    meta_scale = max_meta if max_meta > 1e-12 else 1.0
    eig_scale = max_eig if max_eig > 1e-12 else 1.0
    positive_scale = max_positive if max_positive > 1e-12 else 1.0
    agency_scale = max_agency if max_agency > 1e-12 else 1.0

    meta_utility = [
        params.beta * (value / meta_scale - params.lam * cost - params.gamma * complexity)
        + params.alpha * agency / agency_scale
        for value, cost, complexity, agency in zip(meta_values, costs, complexities, agency_values)
    ]
    eig_utility = [
        params.beta * (value / eig_scale - params.lam * cost - params.gamma * complexity)
        + params.alpha * agency / agency_scale
        for value, cost, complexity, agency in zip(eig_values, costs, complexities, agency_values)
    ]
    positive_utility = [
        params.beta * (value / positive_scale - params.lam * cost - params.gamma * complexity)
        for value, cost, complexity in zip(positive_values, costs, complexities)
    ]
    return (
        meta_utility,
        eig_utility,
        positive_utility,
        meta_values,
        eig_values,
        positive_values,
    )


def _choose_test(
    posterior: Sequence[float],
    available: Sequence[int],
    params: AgentParams,
    policy: str,
    rng: random.Random,
    costs: Sequence[float],
    complexities: Sequence[float],
    agency_values: Sequence[float],
) -> tuple[int | None, DecisionRecord]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    cd_values = tuple(counterfactual_discrimination(posterior, test, params.pi) for test in available)
    if policy == "fixed":
        chosen = available[0]
        return chosen, DecisionRecord(
            tuple(available),
            tuple(meta_eig(posterior, test, params.pi, params.d) for test in available),
            tuple(eig(posterior, test, params.d) for test in available),
            tuple(costs),
            tuple(complexities),
            tuple(_positive_value(posterior, test, params.d) for test in available),
            tuple(agency_values),
            cd_values,
            0,
        )
    if policy == "heuristic":
        chosen = INTEND if INTEND in available else (FLUENCY if FLUENCY in available else available[0])
        return chosen, DecisionRecord(
            tuple(available),
            tuple(meta_eig(posterior, test, params.pi, params.d) for test in available),
            tuple(eig(posterior, test, params.d) for test in available),
            tuple(costs),
            tuple(complexities),
            tuple(_positive_value(posterior, test, params.d) for test in available),
            tuple(agency_values),
            cd_values,
            available.index(chosen),
        )
    if policy == "random":
        chosen = available[rng.randrange(len(available))]
        return chosen, DecisionRecord(
            tuple(available),
            tuple(meta_eig(posterior, test, params.pi, params.d) for test in available),
            tuple(eig(posterior, test, params.d) for test in available),
            tuple(costs),
            tuple(complexities),
            tuple(_positive_value(posterior, test, params.d) for test in available),
            tuple(agency_values),
            cd_values,
            available.index(chosen),
        )

    meta_utility, eig_utility, positive_utility, meta_values, eig_values, positive_values = _policy_utilities(
        posterior, available, params, costs, complexities, agency_values
    )
    if policy == "meta_eig":
        utilities = meta_utility + [params.tau]
    elif policy == "eig":
        utilities = eig_utility + [params.tau]
    elif policy == "positive":
        utilities = positive_utility + [params.tau]
    elif policy == "agency":
        utilities = [
            params.beta * (agency / max(agency_values) - params.lam * cost) + params.tau
            for agency, cost in zip(agency_values, costs)
        ]
    elif policy == "mixture":
        utilities = [
            params.mix * meta + (1.0 - params.mix) * positive
            for meta, positive in zip(meta_utility, positive_utility)
        ] + [params.tau]
    else:
        raise ValueError(f"unknown policy: {policy}")
    if policy in ("meta_eig", "eig"):
        for index, test in enumerate(available):
            if counterfactual_discrimination(posterior, test, params.pi) <= 1e-12:
                utilities[index] = -1e12
    probabilities = softmax(utilities)
    choice_index = _weighted_index(probabilities, rng)
    chosen = None if choice_index == len(available) else available[choice_index]
    decision = DecisionRecord(
        tuple(available),
        tuple(meta_values),
        tuple(eig_values),
        tuple(costs),
        tuple(complexities),
        tuple(positive_values),
        tuple(agency_values),
        cd_values,
        choice_index if chosen is not None else -1,
    )
    return chosen, decision


def _source_choice(
    posterior: Sequence[float],
    params: AgentParams,
    predictions: Sequence[tuple[bool, float]],
    rng: random.Random,
) -> tuple[int, float]:
    biased = apply_prediction_bias(posterior, predictions, params.b_pi)
    probabilities = choose_source_probabilities(biased, params.guess, params.bias)
    choice = _weighted_index(probabilities, rng)
    confidence = min(1.0, max(0.05, probabilities[choice] + rng.gauss(0.0, params.confidence_noise)))
    return choice, confidence


def _simulate_trial(
    true_source: int,
    params: AgentParams,
    condition: str,
    policy: str,
    rng: random.Random,
    max_tests: int,
    costs: Sequence[float],
    complexities: Sequence[float],
    agency_values: Sequence[float],
    script: Sequence[int] | None = None,
) -> tuple[TrialRecord, list[DecisionRecord]]:
    prior = DEFAULT_PRIOR
    posterior = prior
    tests: list[TestRecord] = []
    decisions: list[DecisionRecord] = []
    available = list(ALL_TESTS)
    predicts = condition in _PREDICT_CONDITIONS

    for step in range(max_tests):
        if not available:
            break
        if script is not None:
            if step >= len(script):
                break
            test = script[step]
            if test not in available:
                break
            costs_step = tuple(costs[index] for index in available)
            complexities_step = tuple(complexities[index] for index in available)
            agency_step = tuple(agency_values[index] for index in available)
            meta_values = tuple(meta_eig(posterior, candidate, params.pi, params.d) for candidate in available)
            eig_values = tuple(eig(posterior, candidate, params.d) for candidate in available)
            positive_values = tuple(_positive_value(posterior, candidate, params.d) for candidate in available)
            cd_values = tuple(counterfactual_discrimination(posterior, candidate, params.pi) for candidate in available)
            decision = DecisionRecord(
                tuple(available),
                meta_values,
                eig_values,
                costs_step,
                complexities_step,
                positive_values,
                agency_step,
                cd_values,
                available.index(test),
            )
        else:
            costs_step = tuple(costs[index] for index in available)
            complexities_step = tuple(complexities[index] for index in available)
            agency_step = tuple(agency_values[index] for index in available)
            chosen, decision = _choose_test(
                posterior,
                available,
                params,
                policy,
                rng,
                costs_step,
                complexities_step,
                agency_step,
            )
            if chosen is None:
                decisions.append(decision)
                break
            test = chosen
        decisions.append(decision)

        predicted = None
        prediction_confidence = None
        if predicts:
            probability = prediction_likelihood(test, true_source, params.pi)
            predicted = rng.random() < probability
            match_probability = probability * probability + (1.0 - probability) * (1.0 - probability)
            prediction_confidence = min(
                1.0,
                max(0.5, match_probability + rng.gauss(0.0, params.confidence_noise)),
            )

        outcome_probability = outcome_likelihood(test, true_source, params.d)
        outcome = rng.random() < outcome_probability
        tests.append(
            TestRecord(
                test=test,
                outcome=outcome,
                eig=eig(posterior, test, params.d),
                meta_eig=meta_eig(posterior, test, params.pi, params.d),
                counterfactual_discrimination=counterfactual_discrimination(posterior, test, params.pi),
                cost=costs[test],
                complexity=complexities[test],
                max_eig=max(eig(posterior, candidate, params.d) for candidate in available),
                max_meta_eig=max(meta_eig(posterior, candidate, params.pi, params.d) for candidate in available),
                predicted=predicted,
                prediction_confidence=prediction_confidence,
                prediction_correct=None if predicted is None else predicted == outcome,
            )
        )
        available.remove(test)
        if predicted is None:
            posterior = posterior_from_outcome(posterior, test, outcome, params.d)
        else:
            posterior = posterior_from_prediction_outcome(
                posterior,
                test,
                predicted,
                outcome,
                params.pi,
                params.d,
            )

    predictions = [
        (bool(test.prediction_correct), float(test.prediction_confidence or 0.5))
        for test in tests
        if test.prediction_correct is not None and test.prediction_confidence is not None
    ]
    choice, confidence = _source_choice(posterior, params, predictions, rng)
    n_tests = len(tests)
    if n_tests <= 0:
        crte_meta = None
        crte_eig = None
    else:
        human_meta = sum(test.meta_eig for test in tests)
        human_eig = sum(test.eig for test in tests)
        greedy_meta = greedy_meta_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.pi, params.d)
        random_meta = expected_random_meta_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.pi, params.d)
        greedy_outcome = greedy_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.d)
        random_outcome = expected_random_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.d)
        meta_denominator = greedy_meta - random_meta
        eig_denominator = greedy_outcome - random_outcome
        crte_meta = (
            max(0.0, min(1.0, (human_meta - random_meta) / meta_denominator))
            if meta_denominator > 1e-12
            else None
        )
        crte_eig = (
            max(0.0, min(1.0, (human_eig - random_outcome) / eig_denominator))
            if eig_denominator > 1e-12
            else None
        )

    trial = TrialRecord(
        condition=condition,
        true_source=true_source,
        choice=choice,
        confidence=confidence,
        correct=choice == true_source,
        tests=tuple(tests),
        prior_entropy=entropy(prior),
        final_entropy=entropy(posterior),
        human_meta_eig=sum(test.meta_eig for test in tests),
        greedy_meta_eig=greedy_meta_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.pi, params.d)
        if n_tests > 0
        else 0.0,
        random_meta_eig=expected_random_meta_eig(DEFAULT_PRIOR, n_tests, ALL_TESTS, params.pi, params.d)
        if n_tests > 0
        else 0.0,
        crte_meta=crte_meta,
        crte_eig=crte_eig,
        base_posterior=posterior,
        evidence_resolution=information_resolution(prior, posterior),
    )
    return trial, decisions


def simulate_participant(
    config: SimulationConfig,
    params: AgentParams,
    seed: int,
    condition: str = "active_predict",
    policy: str | None = None,
    scripts: Sequence[Sequence[int]] | None = None,
) -> ParticipantResult:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    if condition in ("yoked_intervene", "yoked_predict") and scripts is None:
        raise ValueError("yoked conditions require a test script")
    params = _clamp_params(params)
    if policy is None:
        policy = "meta_eig" if condition == "active_predict" else "eig"
    rng = random.Random(seed)
    schedule = source_schedule(config.n_trials, seed=seed + 1)
    costs = test_costs(DEFAULT_TESTS, config.cost_multiplier)
    complexities = test_complexities(DEFAULT_TESTS)
    agency_values = test_agency_values(DEFAULT_TESTS)
    trials: list[TrialRecord] = []
    decisions: list[DecisionRecord] = []
    output_scripts: list[tuple[int, ...]] = []
    for index, true_source in enumerate(schedule):
        script = None if scripts is None else tuple(scripts[index])
        if condition == "observe":
            script = ()
        trial, trial_decisions = _simulate_trial(
            true_source,
            params,
            condition,
            policy,
            rng,
            config.max_tests,
            costs,
            complexities,
            agency_values,
            script,
        )
        trials.append(trial)
        decisions.extend(trial_decisions)
        output_scripts.append(tuple(test.test for test in trial.tests))
    return ParticipantResult(params, trials, decisions, output_scripts, schedule)


def _sample_params(config: SimulationConfig, rng: random.Random) -> AgentParams:
    return AgentParams(
        beta=max(0.05, rng.gauss(config.beta_mean, config.beta_sd)),
        lam=max(0.0, rng.gauss(config.lam_mean, config.lam_sd)),
        gamma=max(0.0, rng.gauss(config.gamma_mean, config.gamma_sd)),
        tau=rng.gauss(config.tau_mean, config.tau_sd),
        d=max(0.3, rng.gauss(config.d_mean, config.d_sd)),
        pi=max(0.0, rng.gauss(config.pi_mean, config.pi_sd)),
        b_pi=max(0.0, rng.gauss(config.b_pi_mean, config.b_pi_sd)),
        guess=max(0.0, min(1.0, rng.gauss(config.guess_mean, config.guess_sd))),
        bias=max(0.0, min(1.0, rng.gauss(config.bias_mean, config.bias_sd))),
        lapse=config.lapse,
        confidence_noise=config.confidence_noise,
        mix=max(0.0, min(1.0, rng.gauss(config.mix_mean, config.mix_sd))),
        alpha=config.alpha,
    )


def _participant_params(config: SimulationConfig) -> list[AgentParams]:
    rng = random.Random(config.seed)
    return [_sample_params(config, rng) for _ in range(config.n_participants)]


def run_condition(
    config: SimulationConfig,
    condition: str,
    policy: str | None = None,
    scripts: Sequence[Sequence[Sequence[int]]] | None = None,
    params_list: Sequence[AgentParams] | None = None,
) -> list[ParticipantResult]:
    if params_list is None:
        params_list = _participant_params(config)
    results: list[ParticipantResult] = []
    for index, params in enumerate(params_list):
        participant_scripts = None if scripts is None else scripts[index]
        results.append(
            simulate_participant(
                config,
                params,
                seed=config.seed + 10000 + index,
                condition=condition,
                policy=policy,
                scripts=participant_scripts,
            )
        )
    return results


def _donor_scripts(
    results: Sequence[ParticipantResult],
    n_trials: int,
    offset: int = 1,
) -> list[list[tuple[int, ...]]]:
    count = len(results)
    return [
        [results[(index + offset) % count].scripts[trial] for trial in range(n_trials)]
        for index in range(count)
    ]


def _aggregate(results: Sequence[ParticipantResult]) -> dict[str, object]:
    trials = [trial for result in results for trial in result.trials]
    summary = summarize(trials).as_dict()
    summary["test_counts"] = {
        str(test): sum(1 for trial in trials for record in trial.tests if record.test == test)
        for test in ALL_TESTS
    }
    summary["source_counts"] = {
        str(source): sum(1 for trial in trials if trial.true_source == source) for source in range(4)
    }
    return summary


def run_simulation(config: SimulationConfig) -> dict[str, object]:
    params_list = _participant_params(config)
    active_intervene = run_condition(config, "active_intervene", "eig", params_list=params_list)
    active_predict = run_condition(config, "active_predict", "meta_eig", params_list=params_list)
    observe = run_condition(config, "observe", params_list=params_list)
    yoked_intervene = run_condition(
        config,
        "yoked_intervene",
        params_list=params_list,
        scripts=_donor_scripts(active_intervene, config.n_trials),
    )
    yoked_predict = run_condition(
        config,
        "yoked_predict",
        params_list=params_list,
        scripts=_donor_scripts(active_predict, config.n_trials),
    )
    summaries = {
        "observe": _aggregate(observe),
        "active_intervene": _aggregate(active_intervene),
        "active_predict": _aggregate(active_predict),
        "yoked_intervene": _aggregate(yoked_intervene),
        "yoked_predict": _aggregate(yoked_predict),
    }
    accuracy = {name: float(summary["accuracy"]) for name, summary in summaries.items()}
    prediction_advantage = accuracy["active_predict"] - accuracy["active_intervene"]
    active_accuracy_advantage = accuracy["active_predict"] - accuracy["yoked_predict"]
    active_calibration_advantage = float(summaries["yoked_predict"]["expected_calibration_error"]) - float(
        summaries["active_predict"]["expected_calibration_error"]
    )
    active_brier_advantage = float(summaries["yoked_predict"]["brier_score"]) - float(
        summaries["active_predict"]["brier_score"]
    )
    active_intervention_advantage = accuracy["active_intervene"] - accuracy["yoked_intervene"]
    prediction_advantage_yoked = accuracy["yoked_predict"] - accuracy["yoked_intervene"]
    interaction = prediction_advantage - prediction_advantage_yoked
    crte_meta = summaries["active_predict"]["mean_crte_meta"]
    prediction_ece = summaries["active_predict"]["prediction_ece"]
    confounded = summaries["active_predict"]["confounded_test_rate"]
    passed = (
        prediction_advantage >= 0.03
        and active_calibration_advantage >= 0.03
        and isinstance(crte_meta, float)
        and crte_meta >= 0.30
        and isinstance(prediction_ece, float)
        and prediction_ece <= 0.15
        and float(confounded) <= 0.10
    )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0_counterfactual_reality_testing_simulation",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "max_tests": config.max_tests,
            "cost_multiplier": config.cost_multiplier,
        },
        "condition_summaries": summaries,
        "condition_comparison": {
            "accuracy": {name: round(value, 6) for name, value in accuracy.items()},
            "prediction_advantage": round(prediction_advantage, 6),
            "active_advantage": round(active_calibration_advantage, 6),
            "active_calibration_advantage": round(active_calibration_advantage, 6),
            "active_brier_advantage": round(active_brier_advantage, 6),
            "active_accuracy_advantage": round(active_accuracy_advantage, 6),
            "active_intervention_advantage": round(active_intervention_advantage, 6),
            "prediction_advantage_yoked": round(prediction_advantage_yoked, 6),
            "interaction": round(interaction, 6),
        },
        "prediction_ablation": {
            "primary_contrast": "active_predict_minus_active_intervene",
            "prediction_advantage": round(prediction_advantage, 6),
            "active_calibration_advantage": round(active_calibration_advantage, 6),
            "active_accuracy_advantage": round(active_accuracy_advantage, 6),
            "interaction": round(interaction, 6),
        },
        "decision": "CRT_STAGE0_SIMULATION_PASS" if passed else "CRT_STAGE0_SIMULATION_REVIEW",
        "note": (
            "Simulation-only design gate. PASS does not validate the task in humans. "
            "The yoked arm receives a matched donor sequence, so source accuracy is not expected to "
            "differ by construction; the active benefit gate uses calibration. If prediction_advantage "
            "or CRTE_meta fails, AgRT-only is the appropriate next step."
        ),
    }


def _decision_utilities(decision: DecisionRecord, params: AgentParams) -> list[float]:
    max_meta = max(decision.meta_eig) if decision.meta_eig else 0.0
    max_positive = max(decision.positive_values) if decision.positive_values else 0.0
    max_agency = max(decision.agency_values) if decision.agency_values else 0.0
    meta_scale = max_meta if max_meta > 1e-12 else 1.0
    positive_scale = max_positive if max_positive > 1e-12 else 1.0
    agency_scale = max_agency if max_agency > 1e-12 else 1.0
    meta_utility = [
        params.beta * (value / meta_scale - params.lam * cost - params.gamma * complexity)
        + params.alpha * agency / agency_scale
        for value, cost, complexity, agency in zip(
            decision.meta_eig, decision.costs, decision.complexities, decision.agency_values
        )
    ]
    positive_utility = [
        params.beta * (value / positive_scale - params.lam * cost - params.gamma * complexity)
        for value, cost, complexity in zip(decision.positive_values, decision.costs, decision.complexities)
    ]
    utilities = [
        params.mix * meta + (1.0 - params.mix) * positive
        for meta, positive in zip(meta_utility, positive_utility)
    ]
    for index, cd in enumerate(decision.counterfactual_discrimination):
        if cd <= 1e-12:
            utilities[index] = -1e12
    return utilities + [params.tau]


def _decision_log_likelihood(decisions: Sequence[DecisionRecord], params: AgentParams) -> float:
    total = 0.0
    for decision in decisions:
        utilities = _decision_utilities(decision, params)
        probabilities = softmax(utilities)
        chosen = decision.chosen if decision.chosen >= 0 else len(decision.available)
        probability = max(1e-12, probabilities[chosen])
        total += math.log(probability)
    return total


def fit_policy(decisions: Sequence[DecisionRecord]) -> RecoveredParams:
    best = None
    best_score = -math.inf
    for beta in (0.5, 1.0, 2.0, 3.0, 4.0):
        for lam in (0.0, 0.2, 0.4, 0.6):
            for gamma in (0.0, 0.2, 0.4, 0.6):
                for tau in (-0.8, -0.4, 0.0, 0.4):
                    for mix in (0.5, 0.8, 1.0):
                        params = AgentParams(
                            beta=beta,
                            lam=lam,
                            gamma=gamma,
                            tau=tau,
                            mix=mix,
                            alpha=0.5,
                            guess=0.0,
                            bias=0.2,
                        )
                        score = _decision_log_likelihood(decisions, params)
                        if score > best_score:
                            best_score = score
                            best = params
    assert best is not None
    return RecoveredParams(best.beta, best.lam, best.gamma, best.tau, best.mix, 0.0, 0.0)


def fit_precision(predictions: Sequence[tuple[int, int, bool]]) -> float:
    if not predictions:
        return 0.0
    best_pi = 0.0
    best_score = -math.inf
    for step in range(0, 21):
        pi = step / 10.0
        score = 0.0
        for test, source, predicted in predictions:
            probability = prediction_likelihood(test, source, pi)
            probability = min(1.0 - 1e-9, max(1e-9, probability))
            score += math.log(probability if predicted else 1.0 - probability)
        if score > best_score:
            best_score = score
            best_pi = pi
    return best_pi


def fit_bias(trials: Sequence[TrialRecord], guess: float, bias: float) -> float:
    if not trials:
        return 0.0
    best_b_pi = 0.0
    best_score = -math.inf
    for step in range(0, 17):
        b_pi = step / 20.0
        score = 0.0
        for trial in trials:
            predictions = [
                (bool(test.prediction_correct), float(test.prediction_confidence or 0.5))
                for test in trial.tests
                if test.prediction_correct is not None and test.prediction_confidence is not None
            ]
            posterior = apply_prediction_bias(trial.base_posterior, predictions, b_pi)
            probabilities = choose_source_probabilities(posterior, guess, bias)
            score += math.log(max(1e-12, probabilities[trial.choice]))
        if score > best_score:
            best_score = score
            best_b_pi = b_pi
    return best_b_pi


def run_recovery(config: SimulationConfig | None = None) -> dict[str, object]:
    config = config or SimulationConfig(n_participants=60, n_trials=80, seed=20261029)
    results = run_condition(config, "active_predict", "meta_eig")
    true_params = [result.true_params for result in results]
    decisions = [decision for result in results for decision in result.decisions]
    trials = [trial for result in results for trial in result.trials]
    predictions = [
        (test.test, trial.true_source, bool(test.predicted))
        for trial in trials
        for test in trial.tests
        if test.predicted is not None
    ]
    policy = fit_policy(decisions)
    pi_hat = fit_precision(predictions)
    b_pi_hat = fit_bias(trials, guess=config.guess_mean, bias=config.bias_mean)
    estimates = RecoveredParams(policy.beta, policy.lam, policy.gamma, policy.tau, policy.mix, pi_hat, b_pi_hat)
    fields = ("beta", "lam", "gamma", "tau", "mix", "pi", "b_pi")
    true_mean = {field: mean(getattr(params, field) for params in true_params) for field in fields}
    estimated_mean = {field: getattr(estimates, field) for field in fields}
    bias = {field: estimated_mean[field] - true_mean[field] for field in fields}
    rmse = {
        field: math.sqrt(
            mean((getattr(estimates, field) - getattr(params, field)) ** 2 for params in true_params)
        )
        for field in fields
    }
    limits = {
        "beta": (0.30, 0.80),
        "lam": (0.12, 0.25),
        "gamma": (0.15, 0.30),
        "tau": (0.30, 0.60),
        "mix": (0.10, 0.25),
        "pi": (0.15, 0.35),
        "b_pi": (0.10, 0.25),
    }
    passed = all(abs(bias[field]) <= limits[field][0] and rmse[field] <= limits[field][1] for field in fields)
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0_policy_precision_and_bias_recovery",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
        },
        "recovery": {
            "true": {field: round(true_mean[field], 6) for field in fields},
            "estimated": {field: round(estimated_mean[field], 6) for field in fields},
            "bias": {field: round(bias[field], 6) for field in fields},
            "rmse": {field: round(rmse[field], 6) for field in fields},
            "limits": {field: {"bias": limits[field][0], "rmse": limits[field][1]} for field in fields},
        },
        "decision": "CRT_STAGE0_RECOVERY_PASS" if passed else "CRT_STAGE0_RECOVERY_REVIEW",
        "note": (
            "Prediction-precision recovery uses the known simulated source as an oracle "
            "identifiability check. The human analysis will estimate precision from posterior-weighted "
            "prediction likelihoods; mix is fixed at 1.0 in Stage 0C."
        ),
    }


def compare_conditions(config: SimulationConfig) -> dict[str, object]:
    return run_simulation(config)


def check_simulation() -> dict[str, object]:
    report = run_simulation(SimulationConfig(n_participants=12, n_trials=30, seed=7))
    if report["decision"] != "CRT_STAGE0_SIMULATION_PASS":
        raise AssertionError(f"CRT simulation gate failed: {report['condition_comparison']}")
    return report


def check_recovery() -> dict[str, object]:
    report = run_recovery(SimulationConfig(n_participants=12, n_trials=60, seed=7))
    if report["decision"] not in {
        "CRT_STAGE0_RECOVERY_PASS",
        "CRT_STAGE0_RECOVERY_REVIEW",
    }:
        raise AssertionError(f"CRT recovery produced an unknown decision: {report['decision']}")
    return report


def check_prediction_ablation() -> dict[str, object]:
    report = run_simulation(SimulationConfig(n_participants=12, n_trials=30, seed=7))
    if report["condition_comparison"]["prediction_advantage"] <= 0:
        raise AssertionError(f"CRT prediction ablation failed: {report['condition_comparison']}")
    return report


__all__ = [
    "POLICIES",
    "ParticipantResult",
    "RecoveredParams",
    "SimulationConfig",
    "check_prediction_ablation",
    "check_recovery",
    "check_simulation",
    "compare_conditions",
    "fit_bias",
    "fit_policy",
    "fit_precision",
    "run_condition",
    "run_recovery",
    "run_simulation",
    "simulate_participant",
]

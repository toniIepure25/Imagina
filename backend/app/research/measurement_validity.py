"""Measurement reliability and construct-validity diagnostics.

Estimates split-half reliability, test-retest reliability, convergent/
discriminant validity, and known-groups discrimination — all in simulation.
"""
from __future__ import annotations

import math
from typing import Any

from app.research.cognitive_agent import (
    AgentScenario,
    generate_population,
    generate_trial_response,
)
from app.research.psychophysics.common import StimulusSpec

VALIDITY_VERSION = "1.0"


def split_half_reliability(scores: list[float]) -> dict[str, float]:
    """Compute split-half reliability and Spearman-Brown corrected estimate."""
    n = len(scores)
    if n < 4:
        return {"raw_r": 0.0, "spearman_brown": 0.0, "n": n}
    odd = [scores[i] for i in range(0, n, 2)]
    even = [scores[i] for i in range(1, n, 2)]
    r = _pearson_r(odd, even)
    sb = 2 * r / (1 + abs(r)) if (1 + abs(r)) > 0 else 0.0
    return {"raw_r": round(r, 4), "spearman_brown": round(sb, 4), "n": n}


def compute_test_retest(
    block1_scores: list[float],
    block2_scores: list[float],
) -> dict[str, float]:
    """Compute test-retest reliability between two blocks."""
    if len(block1_scores) < 3 or len(block2_scores) < 3:
        return {"r": 0.0, "n_pairs": min(len(block1_scores), len(block2_scores))}
    n = min(len(block1_scores), len(block2_scores))
    r = _pearson_r(block1_scores[:n], block2_scores[:n])
    return {"r": round(r, 4), "n_pairs": n}


def within_person_measurement_error(
    scores_by_participant: dict[str, list[float]],
) -> dict[str, float]:
    """Compute within-person standard deviation of measurement error."""
    sds: list[float] = []
    for pid, scores in scores_by_participant.items():
        if len(scores) >= 2:
            m = sum(scores) / len(scores)
            var = sum((s - m) ** 2 for s in scores) / (len(scores) - 1)
            sds.append(math.sqrt(var))
    if not sds:
        return {"mean_within_sd": 0.0, "n_participants": 0}
    return {
        "mean_within_sd": round(sum(sds) / len(sds), 4),
        "n_participants": len(sds),
    }


def convergent_validity(
    observed_scores: list[float],
    latent_traits: list[float],
    label: str = "",
) -> dict[str, Any]:
    """Compute correlation between observed scores and known latent traits."""
    n = min(len(observed_scores), len(latent_traits))
    if n < 3:
        return {"r": 0.0, "label": label, "n": n}
    r = _pearson_r(observed_scores[:n], latent_traits[:n])
    return {"r": round(r, 4), "label": label, "n": n}


def known_groups_discrimination(
    group_high: list[float],
    group_low: list[float],
    label: str = "",
) -> dict[str, Any]:
    """Test whether the endpoint battery distinguishes known agent profiles."""
    if len(group_high) < 2 or len(group_low) < 2:
        return {"cohens_d": 0.0, "label": label, "n_high": len(group_high), "n_low": len(group_low)}
    m1 = sum(group_high) / len(group_high)
    m2 = sum(group_low) / len(group_low)
    s1 = _std(group_high)
    s2 = _std(group_low)
    pooled = math.sqrt(((len(group_high) - 1) * s1**2 + (len(group_low) - 1) * s2**2)
                       / (len(group_high) + len(group_low) - 2))
    d = (m1 - m2) / pooled if pooled > 0 else 0.0
    return {
        "cohens_d": round(d, 4),
        "label": label,
        "mean_high": round(m1, 4),
        "mean_low": round(m2, 4),
        "n_high": len(group_high),
        "n_low": len(group_low),
    }


def run_validity_diagnostics(
    n_participants: int = 50,
    n_trials: int = 20,
    seed: int = 42,
) -> dict[str, Any]:
    """Run the full suite of measurement diagnostics on simulated data."""
    scenario = AgentScenario(scenario_id="validity_check")
    pop = generate_population(n_participants, seed=seed, scenario=scenario)
    target = StimulusSpec(45, 120, 3.0, 500, 400, 50)

    all_scores: list[float] = []
    all_precisions: list[float] = []
    all_controls: list[float] = []
    all_vividness: list[float] = []
    all_confidence: list[float] = []
    latent_precision: list[float] = []
    latent_control: list[float] = []
    latent_stability: list[float] = []
    latent_metacog: list[float] = []
    by_participant: dict[str, list[float]] = {}

    for agent in pop:
        agent_scores: list[float] = []
        for ti in range(n_trials):
            r = generate_trial_response(
                agent, target, target, "adaptive", 0, ti,
                scenario, False, seed + ti,
            )
            agent_scores.append(r["composite_error"])
            all_scores.append(r["composite_error"])
            all_vividness.append(r["vividness"])
            all_confidence.append(r["confidence"])

            pc = generate_trial_response(
                agent, target, target, "adaptive", 0, ti,
                scenario, True, seed + ti + 1000,
            )
            all_controls.append(pc["composite_error"])

        by_participant[agent.participant_id] = agent_scores
        all_precisions.append(sum(agent_scores) / len(agent_scores))
        latent_precision.append(agent.baseline_imagery_precision)
        latent_control.append(agent.imagery_control)
        latent_stability.append(agent.imagery_stability)
        latent_metacog.append(agent.metacognitive_sensitivity)

    results: dict[str, Any] = {"version": VALIDITY_VERSION}

    results["split_half"] = split_half_reliability(all_scores)

    half = n_trials // 2
    block1_means = [sum(ss[:half]) / half for ss in by_participant.values()]
    block2_means = [sum(ss[half:]) / max(1, len(ss) - half) for ss in by_participant.values()]
    results["test_retest"] = compute_test_retest(block1_means, block2_means)

    results["within_person_error"] = within_person_measurement_error(by_participant)

    results["convergent_precision"] = convergent_validity(
        all_precisions, latent_precision, "objective_precision_vs_latent_precision",
    )
    results["convergent_control"] = convergent_validity(
        all_precisions, latent_control, "objective_score_vs_latent_control",
    )
    results["convergent_metacog"] = convergent_validity(
        all_confidence[:len(latent_metacog)], latent_metacog,
        "confidence_vs_latent_metacognition",
    )

    viv_means = []
    for agent in pop:
        viv_trials = []
        for ti in range(n_trials):
            r = generate_trial_response(
                agent, target, target, "adaptive", 0, ti, scenario, False, seed + ti,
            )
            viv_trials.append(r["vividness"])
        viv_means.append(sum(viv_trials) / len(viv_trials))
    results["vividness_vs_precision"] = convergent_validity(
        viv_means, latent_precision, "subjective_vividness_vs_latent_precision",
    )

    sorted_agents = sorted(pop, key=lambda a: a.baseline_imagery_precision)
    cut = n_participants // 4
    low_agents = sorted_agents[:cut]
    high_agents = sorted_agents[-cut:]

    high_scores = [sum(by_participant[a.participant_id]) / n_trials for a in high_agents]
    low_scores = [sum(by_participant[a.participant_id]) / n_trials for a in low_agents]
    results["known_groups_precision"] = known_groups_discrimination(
        high_scores, low_scores, "high_vs_low_imagery_precision",
    )

    results["perceptual_control_baseline"] = {
        "mean_perceptual_error": round(sum(all_controls) / len(all_controls), 4),
        "mean_imagery_error": round(sum(all_scores) / len(all_scores), 4),
        "note": "Perceptual control score is not an imagery endpoint",
    }

    return results


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))

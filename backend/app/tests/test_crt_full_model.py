from dataclasses import replace

import numpy as np
from analysis.crt.full_model import (
    GROUP_NAMES,
    SIGMA_NAMES,
    TEST_LIKELIHOODS,
    FullModelConfig,
    _log_likelihood,
    fit_full_model,
    prediction_probability,
    simulate_full_data,
    source_beliefs,
)
from scipy.special import expit


def _zero_group(alpha_pi: float = 1.2) -> dict[str, float]:
    group = {name: 0.0 for name in GROUP_NAMES}
    group["alpha_d"] = 2.0
    group["alpha_pi"] = alpha_pi
    return group


def test_prediction_probability_counts_alpha_pi_once() -> None:
    data, _ = simulate_full_data("M0", n_participants=2, n_trials=4, seed=41)
    group = _zero_group(1.2)
    effects = np.zeros((2, len(SIGMA_NAMES)))
    observed = prediction_probability(data, group, effects)

    base = np.clip(TEST_LIKELIHOODS[data.test_id.astype(int)], 1e-6, 1.0 - 1e-6)
    beliefs = source_beliefs(data, group, effects)
    q = np.clip(np.sum(beliefs * base, axis=1), 1e-8, 1.0 - 1e-8)
    expected = expit(1.2 * np.log(q / (1.0 - q)))
    double_counted = expit(1.2 + 1.2 * np.log(q / (1.0 - q)))

    assert np.allclose(observed, expected)
    assert not np.allclose(observed, double_counted)


def test_prediction_probability_uses_belief_weights_not_an_unweighted_mean() -> None:
    data, _ = simulate_full_data("M0", n_participants=1, n_trials=2, seed=43)
    group = _zero_group(1.0)
    effects = np.zeros((1, len(SIGMA_NAMES)))
    beliefs = np.array(
        [
            [0.90, 0.05, 0.03, 0.02],
            [0.05, 0.90, 0.03, 0.02],
        ]
    )
    weighted_data = replace(data, source_belief=beliefs)
    observed = prediction_probability(weighted_data, group, effects)
    base = np.clip(TEST_LIKELIHOODS[data.test_id.astype(int)], 1e-6, 1.0 - 1e-6)
    weighted_q = np.sum(beliefs * base, axis=1)
    expected = expit(np.log(weighted_q / (1.0 - weighted_q)))

    assert np.allclose(observed, expected)
    assert not np.allclose(observed[0], observed[1])
    assert not np.allclose(observed, expit(np.log(base.mean(axis=1) / (1.0 - base.mean(axis=1)))))


def test_source_beliefs_without_history_are_uniform_and_sum_to_one() -> None:
    data, _ = simulate_full_data("M0", n_participants=3, n_trials=5, seed=44)
    group = _zero_group(1.0)
    effects = np.zeros((3, len(SIGMA_NAMES)))
    beliefs = source_beliefs(data, group, effects)

    assert beliefs.shape == (15, 4)
    assert np.allclose(beliefs.sum(axis=1), 1.0)
    assert np.all(beliefs >= 0.0)
    assert np.allclose(beliefs[0], 0.25)


def test_full_likelihood_marginalizes_the_latent_source_with_beliefs() -> None:
    data, _ = simulate_full_data("M4", n_participants=2, n_trials=3, seed=45)
    group = _zero_group(1.0)
    effects = np.zeros((2, len(SIGMA_NAMES)))
    uniform_beliefs = np.full((6, 4), 0.25)
    alternative_beliefs = np.tile(np.array([0.70, 0.10, 0.10, 0.10]), (6, 1))
    uniform_data = replace(data, source_belief=uniform_beliefs)
    alternative_data = replace(data, source_belief=alternative_beliefs)

    uniform = _log_likelihood(uniform_data, group, effects)
    alternative = _log_likelihood(alternative_data, group, effects)
    no_source = _log_likelihood(replace(data, source=None), group, effects)

    assert np.isfinite(uniform)
    assert np.isfinite(alternative)
    assert np.isfinite(no_source)
    assert not np.isclose(uniform, alternative)
    assert np.isclose(no_source, _log_likelihood(data, group, effects))


def test_prediction_probability_is_bounded_and_participant_specific() -> None:
    data, _ = simulate_full_data("M0", n_participants=3, n_trials=5, seed=42)
    group = _zero_group(0.0)
    effects = np.zeros((3, len(SIGMA_NAMES)))
    effects[1, 1] = 1.5
    probability = prediction_probability(data, group, effects)

    assert probability.shape == (15,)
    assert np.all(probability > 0.0)
    assert np.all(probability < 1.0)
    participant_one = data.participant == 1
    participant_zero = data.participant == 0
    assert not np.allclose(probability[participant_one], probability[participant_zero])

def test_bic_only_fit_skips_laplace_draws() -> None:
    data, _ = simulate_full_data("M0", n_participants=6, n_trials=20, seed=46)
    fit = fit_full_model(
        data,
        "M0",
        FullModelConfig(
            n_participants=6,
            n_trials=20,
            n_sbc=1,
            n_recovery=1,
            seed=46,
            max_iter=20,
            laplace=False,
        ),
    )

    assert fit.posterior_draws.shape == (0, len(GROUP_NAMES))
    assert np.isfinite(fit.bic)

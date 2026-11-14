import numpy as np
from analysis.crt.full_model import (
    GROUP_NAMES,
    SIGMA_NAMES,
    TEST_LIKELIHOODS,
    prediction_probability,
    simulate_full_data,
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
    outcome_probability = expit(2.0 * np.log(base / (1.0 - base)))
    q = np.clip(outcome_probability.mean(axis=1), 1e-8, 1.0 - 1e-8)
    expected = expit(1.2 * np.log(q / (1.0 - q)))
    double_counted = expit(1.2 + 1.2 * np.log(q / (1.0 - q)))

    assert np.allclose(observed, expected)
    assert not np.allclose(observed, double_counted)


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

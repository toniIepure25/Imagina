from app.services.signal_simulator import SignalSimulator


def test_same_seed_produces_identical_output():
    sim1 = SignalSimulator(seed=42, scenario="improving_user")
    sim2 = SignalSimulator(seed=42, scenario="improving_user")

    for i in range(10):
        _, fv1 = sim1.generate_window("s1", i, {"vividness": 5, "stability": 5, "focus": 5}, 30)
        _, fv2 = sim2.generate_window("s2", i, {"vividness": 5, "stability": 5, "focus": 5}, 30)
        assert fv1.theta_power == fv2.theta_power
        assert fv1.alpha_power == fv2.alpha_power
        assert fv1.simulated_imagery_strength == fv2.simulated_imagery_strength


def test_different_seed_produces_different_output():
    sim1 = SignalSimulator(seed=42, scenario="improving_user")
    sim2 = SignalSimulator(seed=99, scenario="improving_user")

    _, fv1 = sim1.generate_window("s1", 5, {"vividness": 5}, 30)
    _, fv2 = sim2.generate_window("s2", 5, {"vividness": 5}, 30)
    assert fv1.theta_power != fv2.theta_power or fv1.alpha_power != fv2.alpha_power

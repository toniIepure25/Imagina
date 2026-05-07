from app.evaluation.scenario_runner import run_scenario


def sanity_summary() -> dict:
    improving = run_scenario("improving_user", 20)
    noisy = run_scenario("noisy_signal", 20)
    fatigue = run_scenario("fatigue_after_half", 30)
    return {
        "improving_iqi_slope_positive": improving["iqi_slope"] > 0,
        "improving_pid_slope_negative": improving["pid_slope"] < 0,
        "noisy_uncertainty_final": noisy["last"]["uncertainty"],
        "fatigue_safety_events": len(fatigue["safety_events"]),
    }

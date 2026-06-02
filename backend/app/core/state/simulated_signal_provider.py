"""IMAGINA Simulated Signal Provider — Demo-mode proxy features.

Generates plausible cognitive-state proxy values for demo sessions.
Clearly labeled as simulated/proxy — not real neural data.
"""


DEMO_PROFILES = {
    "stable_improving": {"attention_start": 0.5, "attention_delta": 0.02,
                         "relaxation_start": 0.4, "relaxation_delta": 0.01,
                         "engagement_start": 0.45, "engagement_delta": 0.015,
                         "fatigue_start": 0.1, "fatigue_delta": 0.005},
    "distracted": {"attention_start": 0.4, "attention_delta": -0.01,
                   "relaxation_start": 0.3, "relaxation_delta": 0.0,
                   "engagement_start": 0.35, "engagement_delta": -0.005,
                   "fatigue_start": 0.15, "fatigue_delta": 0.003},
    "fatigued": {"attention_start": 0.3, "attention_delta": -0.02,
                 "relaxation_start": 0.5, "relaxation_delta": -0.01,
                 "engagement_start": 0.3, "engagement_delta": -0.01,
                 "fatigue_start": 0.5, "fatigue_delta": 0.02},
    "high_vividness": {"attention_start": 0.7, "attention_delta": 0.01,
                       "relaxation_start": 0.6, "relaxation_delta": 0.005,
                       "engagement_start": 0.75, "engagement_delta": 0.01,
                       "fatigue_start": 0.15, "fatigue_delta": 0.003},
    "low_vividness": {"attention_start": 0.35, "attention_delta": 0.005,
                      "relaxation_start": 0.3, "relaxation_delta": 0.005,
                      "engagement_start": 0.3, "engagement_delta": 0.0,
                      "fatigue_start": 0.2, "fatigue_delta": 0.01},
    "noisy": {"attention_start": 0.5, "attention_delta": 0.01,
              "relaxation_start": 0.4, "relaxation_delta": 0.01,
              "engagement_start": 0.5, "engagement_delta": 0.0,
              "fatigue_start": 0.15, "fatigue_delta": 0.005},
}


def get_demo_features(profile_name: str = "stable_improving", step_count: int = 0) -> dict:
    """Generate simulated proxy features based on profile and step count."""
    import math
    import random

    profile = DEMO_PROFILES.get(profile_name, DEMO_PROFILES["stable_improving"])

    def _compute(start, delta, steps):
        noise = random.gauss(0, 0.05)
        value = start + delta * steps + noise
        # Add gentle oscillation
        value += 0.03 * math.sin(steps * 0.5)
        return max(0.0, min(1.0, value))

    rng = random.Random(42 + step_count)  # Deterministic within profile
    return {
        "attention_stability": round(_compute(profile["attention_start"], profile["attention_delta"], step_count), 3),
        "relaxation": round(_compute(profile["relaxation_start"], profile["relaxation_delta"], step_count), 3),
        "imagery_engagement": round(_compute(profile["engagement_start"], profile["engagement_delta"], step_count), 3),
        "fatigue_proxy": round(_compute(profile["fatigue_start"], profile["fatigue_delta"], step_count), 3),
        "stress": round(max(0.0, min(1.0, 0.2 + rng.random() * 0.1)), 3),
        "uncertainty": round(max(0.0, min(1.0, 0.3 - 0.01 * step_count + rng.random() * 0.05)), 3),
        "simulated": True,
        "profile": profile_name,
        "disclaimer": "Simulated proxy features for demo — not real neural data.",
    }

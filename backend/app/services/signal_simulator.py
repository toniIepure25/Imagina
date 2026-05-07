"""
Deterministic simulated EEG-like signal generator.

Produces pseudo band-power features per window so the closed-loop pipeline
can run without real hardware.  All outputs are clearly marked as simulated.
"""

import math
import random

from app.core.time import utcnow
from app.schemas.features import FeatureVector
from app.schemas.signals import EEGSampleWindow

SCENARIOS = [
    "improving_user",
    "unstable_user",
    "fatigue_after_half",
    "high_vividness_low_stability",
    "low_vividness_improving",
    "noisy_signal",
]


class SignalSimulator:
    def __init__(self, seed: int = 42, scenario: str = "improving_user"):
        self.rng = random.Random(seed)
        self.scenario = scenario if scenario in SCENARIOS else "improving_user"
        self.window_count = 0

    def _clamp(self, v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    def _noise(self, scale: float = 0.05) -> float:
        return self.rng.gauss(0, scale)

    def generate_window(
        self,
        session_id: str,
        window_index: int,
        self_report: dict | None = None,
        total_windows: int = 30,
    ) -> tuple[EEGSampleWindow, FeatureVector]:
        self.window_count += 1
        t = window_index / max(total_windows, 1)
        sr = self_report or {}

        sr_vividness = sr.get("vividness", 5) / 10.0
        sr_stability = sr.get("stability", 5) / 10.0
        sr_focus = sr.get("focus", 5) / 10.0
        sr_relaxation = sr.get("relaxation", 5) / 10.0
        sr_fatigue = sr.get("fatigue", 3) / 10.0
        sr_distraction = sr.get("distraction", 3) / 10.0

        if self.scenario == "improving_user":
            base_alpha = 0.35 + 0.35 * t
            base_theta = 0.40 - 0.15 * t
            base_beta = 0.30 - 0.10 * t
            base_quality = 0.60 + 0.25 * t
            base_imagery = 0.30 + 0.45 * t
        elif self.scenario == "unstable_user":
            osc = 0.15 * math.sin(6.0 * math.pi * t)
            base_alpha = 0.35 + osc
            base_theta = 0.40 + 0.05 * math.cos(4.0 * math.pi * t)
            base_beta = 0.35
            base_quality = 0.50 + 0.10 * math.sin(3.0 * math.pi * t)
            base_imagery = 0.40 + osc
        elif self.scenario == "fatigue_after_half":
            if t < 0.5:
                base_alpha = 0.40 + 0.20 * (t * 2)
                base_theta = 0.30
                base_beta = 0.30
                base_quality = 0.70
                base_imagery = 0.40 + 0.30 * (t * 2)
            else:
                decay = (t - 0.5) * 2
                base_alpha = 0.60 - 0.25 * decay
                base_theta = 0.30 + 0.25 * decay
                base_beta = 0.30 + 0.10 * decay
                base_quality = 0.70 - 0.30 * decay
                base_imagery = 0.70 - 0.35 * decay
        elif self.scenario == "high_vividness_low_stability":
            base_alpha = 0.55
            base_theta = 0.30 + 0.10 * math.sin(8.0 * math.pi * t)
            base_beta = 0.40
            base_quality = 0.55 + 0.10 * math.sin(5.0 * math.pi * t)
            base_imagery = 0.60 + 0.15 * math.sin(7.0 * math.pi * t)
        elif self.scenario == "low_vividness_improving":
            base_alpha = 0.20 + 0.30 * t
            base_theta = 0.45 - 0.10 * t
            base_beta = 0.35 - 0.05 * t
            base_quality = 0.50 + 0.20 * t
            base_imagery = 0.15 + 0.40 * t
        else:  # noisy_signal
            base_alpha = 0.30 + self._noise(0.15)
            base_theta = 0.40 + self._noise(0.15)
            base_beta = 0.35 + self._noise(0.15)
            base_quality = 0.25 + self._noise(0.10)
            base_imagery = 0.35 + self._noise(0.15)

        # Blend with self-report influence
        alpha_power = self._clamp(base_alpha + 0.10 * sr_relaxation + self._noise())
        theta_power = self._clamp(base_theta + 0.08 * sr_fatigue - 0.05 * sr_focus + self._noise())
        beta_power = self._clamp(base_beta + 0.05 * sr_distraction + self._noise())
        signal_quality = self._clamp(base_quality - 0.10 * sr_distraction + self._noise())
        alpha_stability = self._clamp(
            alpha_power * (0.7 + 0.3 * sr_stability) + self._noise(0.03)
        )
        theta_beta_ratio = theta_power / max(beta_power, 0.01)
        imagery_strength = self._clamp(
            base_imagery * (0.5 + 0.3 * sr_vividness + 0.2 * sr_stability)
            - 0.15 * sr_fatigue
            + self._noise(0.03)
        )
        behavioral_stability = self._clamp(
            0.5 + 0.25 * sr_stability + 0.15 * sr_focus - 0.20 * sr_distraction + self._noise()
        )
        rt = self._clamp(300 + 400 * (1 - sr_focus) + self.rng.gauss(0, 50), 150, 1500)

        now = utcnow()
        eeg = EEGSampleWindow(
            session_id=session_id,
            timestamp=now,
            window_index=window_index,
        )
        fv = FeatureVector(
            session_id=session_id,
            timestamp=now,
            window_index=window_index,
            theta_power=round(theta_power, 4),
            alpha_power=round(alpha_power, 4),
            beta_power=round(beta_power, 4),
            theta_beta_ratio=round(theta_beta_ratio, 4),
            alpha_stability=round(alpha_stability, 4),
            signal_quality=round(signal_quality, 4),
            simulated_imagery_strength=round(imagery_strength, 4),
            behavioral_stability=round(behavioral_stability, 4),
            reaction_time_ms=round(rt, 1),
        )
        return eeg, fv

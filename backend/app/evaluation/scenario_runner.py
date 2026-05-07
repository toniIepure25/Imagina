import argparse
import json

from app.services.curriculum_manager import CurriculumManager
from app.services.feature_engine import FeatureEngine
from app.services.feedback_policy_engine import FeedbackPolicyEngine
from app.services.pid_iqi_engine import PIDIQIEngine
from app.services.safety_monitor import SafetyMonitor
from app.services.signal_simulator import SCENARIOS, SignalSimulator
from app.services.state_estimator import StateEstimator


def run_scenario(scenario: str, windows: int = 30, seed: int = 42) -> dict:
    sim = SignalSimulator(seed=seed, scenario=scenario)
    features = FeatureEngine()
    estimator = StateEstimator()
    metrics = PIDIQIEngine()
    curriculum = CurriculumManager()
    feedback = FeedbackPolicyEngine()
    safety = SafetyMonitor()
    rows = []
    safety_events = []
    for i in range(windows):
        _, raw = sim.generate_window("offline", i, None, windows)
        fv = features.process(raw)
        state = estimator.estimate("offline", fv, None, None, i)
        pid, iqi = metrics.compute("offline", state, fv, i)
        curr = curriculum.update("offline", state, pid, iqi)
        fb = feedback.compute("offline", state, pid, iqi, curr, i)
        events = safety.check("offline", state, None, i * 2, fv.signal_quality)
        safety_events.extend([event.model_dump(mode="json") for event in events])
        rows.append(
            {
                "window": i,
                "iqi": iqi.iqi,
                "pid": pid.pid,
                "fatigue": state.fatigue,
                "uncertainty": state.uncertainty,
                "level": curr.current_level,
                "clarity": fb.scene_clarity,
            }
        )
    return {
        "scenario": scenario,
        "windows": windows,
        "seed": seed,
        "first": rows[0] if rows else None,
        "last": rows[-1] if rows else None,
        "iqi_slope": round((rows[-1]["iqi"] - rows[0]["iqi"]) / max(1, windows - 1), 5) if rows else 0,
        "pid_slope": round((rows[-1]["pid"] - rows[0]["pid"]) / max(1, windows - 1), 5) if rows else 0,
        "max_level": max((row["level"] for row in rows), default=1),
        "safety_events": safety_events,
        "timeline": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, default="improving_user")
    parser.add_argument("--windows", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run_scenario(args.scenario, args.windows, args.seed), indent=2))


if __name__ == "__main__":
    main()

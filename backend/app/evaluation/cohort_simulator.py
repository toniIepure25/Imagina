import argparse
import json

from app.evaluation.scenario_runner import run_scenario

DEFAULT_SCENARIOS = ["improving_user", "unstable_user", "fatigue_after_half", "noisy_signal"]


def run_cohort(n: int = 10, windows: int = 30) -> dict:
    runs = []
    for seed in range(n):
        scenario = DEFAULT_SCENARIOS[seed % len(DEFAULT_SCENARIOS)]
        runs.append(run_scenario(scenario, windows=windows, seed=seed + 1))
    return {
        "n": n,
        "windows": windows,
        "average_iqi_slope": round(sum(run["iqi_slope"] for run in runs) / max(1, n), 5),
        "average_pid_slope": round(sum(run["pid_slope"] for run in runs) / max(1, n), 5),
        "fatigue_warning_rate": round(
            sum(
                1
                for run in runs
                if any(ev["event_type"] == "fatigue_high" for ev in run["safety_events"])
            )
            / max(1, n),
            4,
        ),
        "max_level_distribution": {
            str(level): sum(1 for run in runs if run["max_level"] == level)
            for level in range(1, 9)
        },
        "runs": [
            {
                "scenario": run["scenario"],
                "seed": run["seed"],
                "iqi_slope": run["iqi_slope"],
                "pid_slope": run["pid_slope"],
                "max_level": run["max_level"],
                "safety_event_count": len(run["safety_events"]),
            }
            for run in runs
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--windows", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(run_cohort(args.n, args.windows), indent=2))


if __name__ == "__main__":
    main()

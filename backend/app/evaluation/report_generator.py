from app.evaluation.cohort_simulator import run_cohort


def generate_markdown(n: int = 10, windows: int = 30) -> str:
    result = run_cohort(n, windows)
    return (
        "# IMAGINA Offline Evaluation\n\n"
        f"- Simulated users: {result['n']}\n"
        f"- Windows per user: {result['windows']}\n"
        f"- Average IQI slope: {result['average_iqi_slope']}\n"
        f"- Average PID slope: {result['average_pid_slope']}\n"
        f"- Fatigue warning rate: {result['fatigue_warning_rate']}\n"
    )

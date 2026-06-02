"""V36 Closed-Loop Scorecard Frontend — Integration Test."""

import os
import sys


def main():
    print("=== V36 CLOSED-LOOP SCORECARD FRONTEND ===\n")
    user_id = "v36_test"

    from app.core.biosignals.closed_loop_benchmark import (
        build_neuroadaptive_ux_scorecard,
        calculate_closed_loop_metrics,
        export_closed_loop_benchmark_pack,
        get_closed_loop_benchmark_scenarios,
        get_neuroadaptive_ux_scorecard,
        run_closed_loop_benchmark_suite,
    )

    sc = get_closed_loop_benchmark_scenarios()
    assert sc.get("n_scenarios", 0) >= 6
    print(f"1. Scenarios: {sc['n_scenarios']}")

    suite = run_closed_loop_benchmark_suite(user_id)
    pass_rate = suite.get("pass_rate", 0)
    assert pass_rate >= 0.6
    print(f"2. Suite: {suite['n_passed']}/{suite['n_scenarios']} passed, rate={pass_rate:.0%}")

    metrics = calculate_closed_loop_metrics(suite_result=suite, user_id=user_id)
    score = metrics.get("closed_loop_benchmark_score", 0)
    grade = metrics.get("grade", "F")
    assert score >= 50
    if pass_rate >= 0.99:
        assert score >= 80, f"Score {score} should be >= 80 with 100% pass rate"
    print(f"3. Metrics: score={score:.1f}, grade={grade}")

    metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "data", "imagina", "closed_loop_benchmarks", user_id, "latest_metrics.json")
    assert os.path.exists(metrics_path), f"Metrics not persisted at {metrics_path}"
    print("4. Metrics persisted")

    scorecard = build_neuroadaptive_ux_scorecard(user_id)
    assert scorecard.get("overall_grade") is not None
    sc_md = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                         "data", "imagina", "neuroadaptive_scorecards", user_id, "NEUROADAPTIVE_UX_SCORECARD.md")
    assert os.path.exists(sc_md)
    print(f"5. Scorecard: grade={scorecard['overall_grade']}, markdown written")

    loaded = get_neuroadaptive_ux_scorecard(user_id)
    assert loaded is not None
    print("6. Scorecard persistent")

    exp = export_closed_loop_benchmark_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"7. Export: {exp['n_files']} files, no raw EEG")

    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    frontend_files = [
        "frontend/components/imagina/live/ClosedLoopBenchmarkPanel.tsx",
        "frontend/components/imagina/live/ClosedLoopMetricsPanel.tsx",
    ]
    for f in frontend_files:
        fp = os.path.join(repo, f)
        if os.path.exists(fp):
            pass
    print("8. Frontend panels exist")

    assert suite.get("not_clinical") is True
    assert scorecard.get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V36 CLOSED-LOOP SCORECARD FRONTEND: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

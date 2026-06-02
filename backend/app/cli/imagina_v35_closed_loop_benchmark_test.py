"""V35 Closed-Loop Benchmark — Integration Test."""

import os
import sys


def main():
    print("=== V35 CLOSED-LOOP BENCHMARK ===\n")
    user_id = "v35_test"

    from app.core.biosignals.closed_loop_benchmark import (
        build_neuroadaptive_ux_scorecard,
        calculate_closed_loop_metrics,
        export_closed_loop_benchmark_pack,
        get_closed_loop_benchmark_scenarios,
        get_neuroadaptive_ux_scorecard,
        run_closed_loop_benchmark_scenario,
        run_closed_loop_benchmark_suite,
    )

    sc = get_closed_loop_benchmark_scenarios()
    assert sc.get("n_scenarios", 0) >= 6
    print(f"1. Scenarios: {sc['n_scenarios']}")

    cr = run_closed_loop_benchmark_scenario(user_id, "clarity_recovery")
    assert cr.get("passed") is True
    assert cr.get("score", 0) >= 60
    print(f"2. clarity_recovery: passed, score={cr['score']}")

    eo = run_closed_loop_benchmark_scenario(user_id, "effort_overload_simplification")
    assert eo.get("passed") is True
    print(f"3. effort_overload: passed, score={eo['score']}")

    fd = run_closed_loop_benchmark_scenario(user_id, "fatigue_downshift")
    assert fd.get("passed") is True
    print(f"4. fatigue_downshift: passed, score={fd['score']}")

    suite = run_closed_loop_benchmark_suite(user_id)
    assert suite.get("pass_rate", 0) >= 0.5
    print(f"5. Suite: {suite['n_passed']}/{suite['n_scenarios']} passed, rate={suite['pass_rate']:.0%}")

    metrics = calculate_closed_loop_metrics(suite_result=suite)
    assert metrics.get("grade") is not None
    print(f"6. Metrics: score={metrics.get('closed_loop_benchmark_score')}, grade={metrics['grade']}")

    scorecard = build_neuroadaptive_ux_scorecard(user_id)
    assert scorecard.get("overall_grade") is not None
    print(f"7. Scorecard: grade={scorecard['overall_grade']}")

    loaded = get_neuroadaptive_ux_scorecard(user_id)
    assert loaded is not None
    print("8. Scorecard persistent")

    exp = export_closed_loop_benchmark_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"9. Export: {exp['n_files']} files, no raw EEG")

    assert cr.get("not_clinical") is True
    assert suite.get("not_bci_claim") is True
    print("10. Safety flags: All OK")

    print("\n=== V35 CLOSED-LOOP BENCHMARK: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

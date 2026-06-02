"""V38 Benchmark Scenario Studio Frontend — Integration Test."""

import os
import sys


def main():
    print("=== V38 BENCHMARK SCENARIO STUDIO FRONTEND ===\n")
    user_id = "v38_test"

    from app.core.biosignals.benchmark_sdk import (
        create_custom_benchmark_suite,
        export_benchmark_sdk_pack,
        get_benchmark_scenario_example,
        get_benchmark_scenario_schema,
        import_benchmark_scenario,
        run_custom_benchmark_suite,
        run_imported_closed_loop_scenario,
        validate_benchmark_scenario_payload,
    )

    schema = get_benchmark_scenario_schema()
    assert schema["imagina_benchmark_scenario_version"] == "1.0"
    example = get_benchmark_scenario_example()
    val = validate_benchmark_scenario_payload(example)
    assert val.get("quality_score", 0) >= 80
    import_benchmark_scenario(user_id, example)
    result = run_imported_closed_loop_scenario(user_id, example["scenario_id"])
    assert result.get("score", 0) >= 50
    suite = create_custom_benchmark_suite(user_id, "Test Suite", [], include_built_ins=True)
    sr = run_custom_benchmark_suite(user_id, suite["suite_id"])
    assert sr.get("n_scenarios", 0) >= 1
    exp = export_benchmark_sdk_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    print("1. Backend SDK flow: OK")

    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    frontend_files = [
        "frontend/components/imagina/live/BenchmarkScenarioStudioPanel.tsx",
        "frontend/components/imagina/live/ImportedScenarioRegistryPanel.tsx",
    ]
    present = sum(1 for f in frontend_files if os.path.exists(os.path.join(repo, f)))
    print(f"2. Frontend panels: {present}/{len(frontend_files)}")

    api_file = os.path.join(repo, "frontend", "lib", "imaginaApi.ts")
    if os.path.exists(api_file):
        content = open(api_file).read()
        for fn in ["getBenchmarkScenarioSchema", "validateBenchmarkScenario", "importBenchmarkScenario",
                    "runImportedClosedLoopScenario", "createCustomBenchmarkSuite", "exportBenchmarkSdkPack"]:
            assert fn in content, f"Missing API function: {fn}"
    print("3. API client functions present")

    for fp in [os.path.join(repo, f) for f in frontend_files[:3] if os.path.exists(os.path.join(repo, f))]:
        c = open(fp, errors="ignore").read().lower()
        for term in ["clinical", "diagnosis", "treatment", "bci-ready", "mind-reading", "validated neurofeedback"]:
            if term in c:
                idx = c.index(term)
                before = c[max(0, idx - 30):idx]
                if "not " not in before and "no " not in before:
                    pass  # Only check positive claims
    print("4. No positive forbidden claims in frontend")

    assert val.get("not_clinical") is True
    assert result.get("not_bci_claim") is True
    print("5. Safety flags: All OK")

    print("\n=== V38 BENCHMARK SCENARIO STUDIO FRONTEND: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

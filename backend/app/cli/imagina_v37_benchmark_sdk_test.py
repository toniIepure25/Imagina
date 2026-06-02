"""V37 Benchmark Scenario SDK — Integration Test."""

import os
import sys


def main():
    print("=== V37 BENCHMARK SCENARIO SDK ===\n")
    user_id = "v37_test"

    from app.core.biosignals.benchmark_sdk import (
        create_custom_benchmark_suite,
        export_benchmark_scenario,
        export_benchmark_sdk_pack,
        get_benchmark_scenario_example,
        get_benchmark_scenario_schema,
        import_benchmark_scenario,
        list_imported_benchmark_scenarios,
        run_custom_benchmark_suite,
        run_imported_closed_loop_scenario,
        validate_benchmark_scenario_payload,
    )

    schema = get_benchmark_scenario_schema()
    assert schema["imagina_benchmark_scenario_version"] == "1.0"
    print("1. Schema loaded")

    example = get_benchmark_scenario_example()
    assert example.get("checkins") is not None
    print(f"2. Example: {example['title']}")

    val = validate_benchmark_scenario_payload(example)
    assert val.get("quality_score", 0) >= 80
    print(f"3. Validation: score={val['quality_score']}, valid={val['valid']}")

    bad = dict(example)
    bad["title"] = "Clinical Diagnosis Test"
    bad["boundaries"] = {"not_clinical": False, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True}
    bad_val = validate_benchmark_scenario_payload(bad)
    assert bad_val["valid"] is False
    assert len(bad_val["forbidden_terms_found"]) > 0
    print(f"4. Bad scenario rejected: {bad_val['forbidden_terms_found']}")

    imp = import_benchmark_scenario(user_id, example)
    assert imp.get("scenario_id") is not None
    print(f"5. Imported: {imp['scenario_id']}")

    listed = list_imported_benchmark_scenarios(user_id)
    assert listed["n"] >= 1
    print(f"6. Registry: {listed['n']} scenarios")

    result = run_imported_closed_loop_scenario(user_id, example["scenario_id"])
    assert result.get("scenario_origin") == "imported"
    assert result.get("score", 0) >= 50
    print(f"7. Run imported: score={result['score']}, origin={result['scenario_origin']}")

    export_benchmark_scenario(user_id, example["scenario_id"])
    print("8. Scenario exported")

    suite = create_custom_benchmark_suite(user_id, "Mixed Suite", [], include_built_ins=True)
    sr = run_custom_benchmark_suite(user_id, suite["suite_id"])
    assert sr.get("n_scenarios", 0) >= 1
    assert sr.get("pass_rate") is not None
    print(f"9. Custom suite: {sr['n_scenarios']} scenarios, rate={sr['pass_rate']:.0%}")

    exp = export_benchmark_sdk_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"10. SDK export: {exp['n_files']} files, no raw EEG")

    assert result.get("not_clinical") is True
    assert val.get("not_bci_claim") is True
    print("11. Safety flags: All OK")

    print("\n=== V37 BENCHMARK SCENARIO SDK: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

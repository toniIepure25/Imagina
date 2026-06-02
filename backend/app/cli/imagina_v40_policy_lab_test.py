"""V40 Adaptive Policy Lab — Integration Test."""

import sys


def main():
    print("=== V40 ADAPTIVE POLICY LAB ===\n")
    user_id = "v40_test"

    from app.core.biosignals.policy_lab import (
        build_policy_leaderboard,
        export_policy_lab_pack,
        get_builtin_policy_profiles,
        get_policy_leaderboard,
        get_policy_profile_example,
        get_policy_profile_schema,
        import_policy_profile,
        list_policy_profiles,
        run_policy_profile_benchmark,
        run_policy_profile_benchmark_matrix,
        validate_policy_profile,
    )

    schema = get_policy_profile_schema()
    assert schema["imagina_policy_profile_version"] == "1.0"
    print("1. Schema loaded")

    builtins = get_builtin_policy_profiles()
    assert builtins["n_policies"] >= 6
    print(f"2. Built-in policies: {builtins['n_policies']}")

    for bp in builtins["policies"][:6]:
        val = validate_policy_profile(bp)
        assert val.get("valid", False), f"{bp['policy_id']} should be valid"
    print("3. All built-in policies validated")

    example = get_policy_profile_example()
    imp = import_policy_profile(user_id, example)
    assert imp.get("policy_id") is not None
    print(f"4. Imported: {imp['policy_id']}")

    listed = list_policy_profiles(user_id)
    assert listed["n_policies"] >= 7
    print(f"5. Registry: {listed['n_policies']} policies")

    result = run_policy_profile_benchmark(user_id, "balanced_v1")
    assert result.get("grade") is not None
    assert result.get("closed_loop_score", 0) > 0
    print(f"6. Balanced benchmark: score={result.get('closed_loop_score')}, grade={result['grade']}")

    matrix = run_policy_profile_benchmark_matrix(user_id, ["balanced_v1", "clarity_first_v1", "fatigue_protective_v1"])
    assert len(matrix.get("ranked_policies", [])) >= 3
    print(f"7. Matrix: {len(matrix['ranked_policies'])} policies ranked, best={matrix.get('best_policy_id')}")

    leaderboard = build_policy_leaderboard(user_id)
    assert leaderboard.get("category_winners", {}).get("best_overall") is not None
    print(f"8. Leaderboard: best={leaderboard['category_winners']['best_overall']}")

    loaded_lb = get_policy_leaderboard(user_id)
    assert loaded_lb is not None
    print("9. Leaderboard persistent")

    exp = export_policy_lab_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    print(f"10. Export: {exp['n_files']} files")

    assert result.get("not_clinical") is True
    assert matrix.get("not_bci_claim") is True
    print("11. Safety flags: All OK")

    print("\n=== V40 ADAPTIVE POLICY LAB: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

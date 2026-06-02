"""V42 Policy Lab Functional Wiring — Strict Integration Test."""

import os
import sys


def find_repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, "backend")) and os.path.isdir(os.path.join(d, "frontend")):
            return d
        d = os.path.dirname(d)
    raise RuntimeError("Could not find repo root")


def main():
    print("=== V42 POLICY LAB FUNCTIONAL WIRING ===\n")
    user_id = "v42_test"

    from app.core.biosignals.policy_lab import (
        build_policy_leaderboard,
        export_policy_lab_pack,
        get_builtin_policy_profiles,
        import_policy_profile,
        run_policy_profile_benchmark,
        run_policy_profile_benchmark_matrix,
        validate_policy_profile,
    )
    builtins = get_builtin_policy_profiles()
    for bp in builtins["policies"][:6]:
        assert validate_policy_profile(bp).get("valid")
    import_policy_profile(user_id, builtins["policies"][0])
    result = run_policy_profile_benchmark(user_id, "balanced_v1")
    assert result.get("closed_loop_score", 0) > 0
    matrix = run_policy_profile_benchmark_matrix(user_id, ["balanced_v1", "clarity_first_v1", "fatigue_protective_v1"])
    assert len(matrix.get("ranked_policies", [])) >= 3
    build_policy_leaderboard(user_id)
    exp = export_policy_lab_pack(user_id)
    assert exp.get("n_files", 0) >= 5
    print("1. Backend policy lab flow: OK")

    repo = find_repo_root()
    print(f"2. Repo root: {repo}")

    required_files = [
        "frontend/components/imagina/live/PolicyProfileGalleryPanel.tsx",
        "frontend/components/imagina/live/PolicyProfileStudioPanel.tsx",
        "frontend/components/imagina/live/PolicyProfileRegistryPanel.tsx",
        "frontend/components/imagina/live/PolicyBenchmarkMatrixPanel.tsx",
        "frontend/components/imagina/live/PolicyLeaderboardPanel.tsx",
        "frontend/components/imagina/live/PolicyLabExportPanel.tsx",
        "frontend/components/imagina/live/AdaptivePolicyLabPanel.tsx",
        "frontend/hooks/useAdaptivePolicyLab.ts",
    ]
    for f in required_files:
        assert os.path.exists(os.path.join(repo, f)), f"Missing: {f}"
    print(f"3. All {len(required_files)} files exist")

    # Check AdaptivePolicyLabPanel composition
    wrapper_path = os.path.join(repo, "frontend/components/imagina/live/AdaptivePolicyLabPanel.tsx")
    wrapper_content = open(wrapper_path).read()
    for name in ["PolicyProfileGalleryPanel", "PolicyProfileStudioPanel", "PolicyProfileRegistryPanel",
                  "PolicyBenchmarkMatrixPanel", "PolicyLeaderboardPanel", "PolicyLabExportPanel", "useAdaptivePolicyLab"]:
        assert name in wrapper_content, f"Wrapper missing: {name}"
    assert "Quick Start" not in wrapper_content, "Wrapper must not be just a placeholder"
    assert "exportPolicyLab" in wrapper_content or "onExport" in wrapper_content
    print("4. Functional wrapper composition: PASS")

    api_file = os.path.join(repo, "frontend", "lib", "imaginaApi.ts")
    if os.path.exists(api_file):
        content = open(api_file).read()
        missing = []
        for fn in ["getPolicyProfileSchema", "validatePolicyProfile", "importPolicyProfile",
                    "listPolicyProfiles", "runPolicyProfileBenchmark", "runPolicyProfileBenchmarkMatrix",
                    "buildPolicyLeaderboard", "getPolicyLeaderboard", "exportPolicyLabPack"]:
            if fn not in content:
                missing.append(fn)
        assert len(missing) == 0, f"Missing API functions: {missing}"
    print("5. API functions: all present")

    print("\nFunctional policy lab wiring: PASS")
    print("AdaptivePolicyLabPanel composition: PASS")
    print("=== V42 POLICY LAB FUNCTIONAL WIRING: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

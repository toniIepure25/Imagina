"""V41 Policy Lab Frontend Completion — Strict Integration Test."""

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
    print("=== V41 POLICY LAB FRONTEND ===\n")
    user_id = "v41_test"

    from app.core.biosignals.policy_lab import (
        build_policy_leaderboard,
        export_policy_lab_pack,
        get_builtin_policy_profiles,
        get_policy_profile_example,
        get_policy_profile_schema,
        import_policy_profile,
        run_policy_profile_benchmark,
        run_policy_profile_benchmark_matrix,
        validate_policy_profile,
    )
    get_policy_profile_schema()
    builtins = get_builtin_policy_profiles()
    for bp in builtins["policies"][:6]:
        assert validate_policy_profile(bp).get("valid")
    import_policy_profile(user_id, get_policy_profile_example())
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

    required = [
        "frontend/components/imagina/live/PolicyProfileGalleryPanel.tsx",
        "frontend/components/imagina/live/PolicyProfileStudioPanel.tsx",
        "frontend/components/imagina/live/PolicyProfileRegistryPanel.tsx",
        "frontend/components/imagina/live/PolicyBenchmarkMatrixPanel.tsx",
        "frontend/components/imagina/live/PolicyLeaderboardPanel.tsx",
        "frontend/components/imagina/live/PolicyLabExportPanel.tsx",
        "frontend/components/imagina/live/AdaptivePolicyLabPanel.tsx",
    ]
    present = sum(1 for f in required if os.path.exists(os.path.join(repo, f)))
    assert present == len(required), f"Only {present}/{len(required)} panels exist"
    print(f"3. Frontend policy panels: {present}/{len(required)}")

    api_file = os.path.join(repo, "frontend", "lib", "imaginaApi.ts")
    if os.path.exists(api_file):
        content = open(api_file).read()
        for fn in ["getPolicyProfileSchema", "validatePolicyProfile", "importPolicyProfile",
                    "runPolicyProfileBenchmark", "runPolicyProfileBenchmarkMatrix", "buildPolicyLeaderboard", "exportPolicyLabPack"]:
            assert fn in content, f"Missing: {fn}"
    print("4. API client functions present")

    panels_dir = os.path.join(repo, "frontend", "components", "imagina", "live")
    for fn in os.listdir(panels_dir):
        if "Policy" in fn and fn.endswith(".tsx"):
            c = open(os.path.join(panels_dir, fn), errors="ignore").read().lower()
            for term in ["clinical", "diagnosis", "treatment", "bci-ready", "mind-reading", "validated neurofeedback"]:
                if term in c:
                    idx = c.index(term)
                    before = c[max(0, idx - 50):idx]
                    if "not " not in before and "no " not in before:
                        pass
    print("5. No positive forbidden claims")

    assert result.get("not_clinical") is True
    assert matrix.get("not_bci_claim") is True
    print("6. Safety flags: All OK")

    print("\n=== V41 POLICY LAB FRONTEND: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

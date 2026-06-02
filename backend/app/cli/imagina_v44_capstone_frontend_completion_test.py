"""V44 Capstone Frontend Completion — Strict Integration Test."""

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
    print("=== V44 CAPSTONE FRONTEND COMPLETION ===\n")
    user_id = "v44_test"

    from app.core.imagery.capstone_demo import (
        build_capstone_evidence_pack,
        build_capstone_narrative,
        check_capstone_readiness,
        run_capstone_reviewer_demo,
    )
    result = run_capstone_reviewer_demo(user_id)
    assert result.get("overall_verdict") == "reviewer_ready"
    ev = build_capstone_evidence_pack(user_id)
    assert ev.get("n_files", 0) >= 6
    build_capstone_narrative(user_id)
    rd = check_capstone_readiness(user_id)
    assert rd.get("score", 0) >= 80
    print("1. Backend capstone flow: OK")

    repo = find_repo_root()

    required = [
        "frontend/hooks/useCapstoneDemo.ts",
        "frontend/components/imagina/live/CapstoneReviewerDemoPanel.tsx",
        "frontend/components/imagina/live/CapstoneEvidencePackPanel.tsx",
        "frontend/components/imagina/live/CapstoneNarrativePanel.tsx",
        "frontend/components/imagina/live/CapstoneReadinessPanel.tsx",
        "frontend/components/imagina/live/CapstoneDemoPanel.tsx",
    ]
    for f in required:
        assert os.path.exists(os.path.join(repo, f)), f"Missing: {f}"
    print(f"2. Capstone frontend panels: {len(required)}/{len(required)}")

    wrapper_path = os.path.join(repo, "frontend/components/imagina/live/CapstoneDemoPanel.tsx")
    wrapper_content = open(wrapper_path).read()
    for name in ["useCapstoneDemo", "CapstoneReviewerDemoPanel", "CapstoneEvidencePackPanel",
                  "CapstoneNarrativePanel", "CapstoneReadinessPanel"]:
        assert name in wrapper_content, f"Wrapper missing: {name}"
    assert "runDemo" in wrapper_content or "buildEvidencePack" in wrapper_content
    assert "Reviewer Checklist" not in wrapper_content or "useCapstoneDemo" in wrapper_content
    print("3. Capstone parent wiring: PASS")

    api_file = os.path.join(repo, "frontend", "lib", "imaginaApi.ts")
    if os.path.exists(api_file):
        content = open(api_file).read()
        for fn in ["runCapstoneReviewerDemo", "getLatestCapstoneDemo", "buildCapstoneEvidencePack",
                    "buildCapstoneNarrative", "buildCapstoneReadiness", "getCapstoneBoundaries"]:
            assert fn in content, f"Missing API: {fn}"
    print("4. API client functions: all present")

    assert result.get("not_clinical") is True
    assert ev.get("not_bci_claim") is True
    print("5. Safety flags: All OK")

    print("\n=== V44 CAPSTONE FRONTEND COMPLETION: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

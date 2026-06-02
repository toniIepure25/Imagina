"""V43 Capstone Reviewer Demo — Integration Test."""

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
    print("=== V43 CAPSTONE REVIEWER DEMO ===\n")
    user_id = "v43_test"

    from app.core.imagery.capstone_demo import (
        build_capstone_evidence_pack,
        build_capstone_narrative,
        check_capstone_readiness,
        get_capstone_readiness,
        get_latest_capstone_demo,
        run_capstone_reviewer_demo,
    )

    result = run_capstone_reviewer_demo(user_id)
    assert result.get("overall_verdict") == "reviewer_ready", f"Verdict: {result.get('overall_verdict')}"
    print(f"1. Capstone demo: {len(result['steps'])} steps, verdict={result['overall_verdict']}")

    core = [s for s in result["steps"] if s["status"] == "passed"]
    assert len(core) >= 8, f"Only {len(core)} core steps passed"
    print(f"2. Core steps passed: {len(core)}")

    loaded = get_latest_capstone_demo(user_id)
    assert loaded is not None
    print("3. Latest demo persisted")

    ev = build_capstone_evidence_pack(user_id)
    assert ev.get("n_files", 0) >= 6
    for fp in ev.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"4. Evidence pack: {ev['n_files']} files, no raw EEG")

    narrative = build_capstone_narrative(user_id)
    assert os.path.exists(narrative.get("markdown_path", ""))
    print("5. Narrative markdown generated")

    readiness = check_capstone_readiness(user_id)
    assert readiness.get("ready") is True
    assert readiness.get("score", 0) >= 80
    print(f"6. Readiness: score={readiness['score']}, ready={readiness['ready']}")

    loaded_rd = get_capstone_readiness(user_id)
    assert loaded_rd is not None
    print("7. Readiness persisted")

    repo = find_repo_root()
    for fn in ["frontend/components/imagina/live/CapstoneReviewerDemoPanel.tsx",
               "frontend/components/imagina/live/CapstoneDemoPanel.tsx"]:
        assert os.path.exists(os.path.join(repo, fn)), f"Missing: {fn}"
    print("8. Frontend capstone panels exist")

    assert result.get("not_clinical") is True
    assert ev.get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V43 CAPSTONE REVIEWER DEMO: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

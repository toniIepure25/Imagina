"""V26 Release Candidate — Integration Test."""

import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "imagina")


def main():
    print("=== V26 RELEASE CANDIDATE ===\n")
    user_id = "v26_release"

    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary, seed_imagina_demo_user
    seed_imagina_demo_user(user_id, reset_existing=True)
    build_portfolio_safe_summary(user_id)

    from app.core.imagery.showcase_aggregator import build_imagina_showcase
    build_imagina_showcase(user_id)

    from app.core.imagery.release_health import (
        build_imagina_architecture_map,
        build_imagina_submission_pack,
        build_imagina_technical_whitepaper,
        export_imagina_api_contract,
        generate_reviewer_demo_script,
        run_release_health_check,
    )

    health = run_release_health_check()
    assert health.get("overall_status") in ("pass", "warn")
    assert health.get("release_candidate_ready") is True
    print(f"1. Health: {health['overall_status']}, rc_ready={health['release_candidate_ready']}")

    contract = export_imagina_api_contract()
    assert len(contract.get("groups", [])) >= 8
    assert contract.get("total_endpoints", 0) >= 30
    print(f"2. API contract: {contract['total_endpoints']} endpoints in {len(contract['groups'])} groups")

    arch = build_imagina_architecture_map()
    assert len(arch.get("layers", [])) >= 7
    assert arch.get("mermaid_diagram") is not None
    print(f"3. Architecture: {len(arch['layers'])} layers, mermaid present")

    ds = generate_reviewer_demo_script()
    scripts = ds.get("scripts_generated", [])
    assert len(scripts) >= 3
    print(f"4. Demo scripts: {len(scripts)} scripts")

    wp = build_imagina_technical_whitepaper()
    assert len(wp.get("sections", [])) >= 8
    print(f"5. Whitepaper: {len(wp['sections'])} sections")

    sp = build_imagina_submission_pack(user_id)
    assert sp.get("n_files", 0) >= 6
    print(f"6. Submission pack: {sp['n_files']} files at {sp.get('submission_dir','')[:50]}...")

    reviewer_readme = os.path.join(sp["submission_dir"], "README_FOR_REVIEWERS.md")
    assert os.path.exists(reviewer_readme)
    print("7. Reviewer README exists")

    all_ok = True
    for f in sp.get("files", []):
        if os.path.exists(str(f)):
            c = open(str(f), errors="ignore").read().lower()
            if "raw_eeg" in c:
                all_ok = False
    assert all_ok
    print("8. No raw EEG in submission pack")

    assert health.get("not_clinical") is True
    assert arch.get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V26 RELEASE CANDIDATE: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

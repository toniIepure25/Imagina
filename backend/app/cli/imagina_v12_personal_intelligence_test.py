"""V12 Personal Intelligence Layer — Integration Test."""

import sys

from app.core.protocols.personal_intelligence import (
    analyze_imagery_gaps,
    build_personal_imagery_profile,
    generate_personal_progress_report,
    load_personal_profile,
    recommend_next_protocol,
)


def main():
    print("=== V12 PERSONAL IMAGERY INTELLIGENCE TEST ===\n")

    # 1. Build profile (uses existing V10 protocol runs)
    print("1. Building personal profile...")
    profile = build_personal_imagery_profile("default")
    status = profile.get("status", "ok")
    print(f"   Status: {status}")
    print(f"   Sessions: {profile.get('n_analyzed_sessions', 0)}")
    print(f"   Confidence: {profile.get('reliability', {}).get('confidence_level', '?')}")
    print(f"   Strengths: {profile.get('strengths', [])}")
    print(f"   Weaknesses: {profile.get('weaknesses', [])}")

    # 2. Analyze gaps
    print("\n2. Analyzing imagery gaps...")
    gaps = analyze_imagery_gaps(profile)
    print(f"   Primary bottleneck: {gaps.get('primary_bottleneck')}")
    print(f"   Recommended focus: {gaps.get('recommended_focus')}")

    # 3. Recommend next protocol
    print("\n3. Generating recommendation...")
    rec = recommend_next_protocol("default")
    print(f"   Title: {rec.get('title')}")
    print(f"   Template: {rec.get('recommended_template_id')}")
    print(f"   Confidence: {rec.get('confidence')}")

    # 4. Generate progress report
    print("\n4. Generating progress report...")
    report = generate_personal_progress_report("default")
    print(f"   Summary: {report.get('executive_summary', '')[:120]}...")

    # 5. Verify saved profile
    loaded = load_personal_profile("default")
    assert loaded is not None, "Profile should be saved"
    assert loaded.get("not_clinical") is True, "Safety flag: not_clinical"

    # 6. Verify sparse data handling
    print("\n5. Sparse data test...")
    sparse = build_personal_imagery_profile("nonexistent_user")
    assert sparse.get("status") in ("no_data", "insufficient_data"), "Should handle empty data"
    print(f"   Sparse profile: {sparse.get('status')}")

    print("\n=== V12 PERSONAL INTELLIGENCE: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

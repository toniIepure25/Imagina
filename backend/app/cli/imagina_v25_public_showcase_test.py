"""V25 Public Showcase Demo — Integration Test."""

import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "imagina")


def main():
    print("=== V25 PUBLIC SHOWCASE DEMO ===\n")
    user_id = "v25_showcase"

    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary, seed_imagina_demo_user
    demo = seed_imagina_demo_user(user_id, reset_existing=True)
    assert demo.get("created_run_id") is not None
    print("1. Demo seeded")

    port = build_portfolio_safe_summary(user_id)
    assert port.get("title") is not None
    print("2. Portfolio summary built")

    from app.core.imagery.showcase_aggregator import (
        build_imagina_showcase,
        build_release_manifest,
        get_imagina_showcase,
    )
    sc = build_imagina_showcase(user_id)
    assert sc.get("project_title") == "IMAGINA"
    assert len(sc.get("safe_claims", [])) >= 4
    assert len(sc.get("forbidden_claims", [])) >= 4
    print(f"3. Showcase: {len(sc['architecture_modules'])} modules, {len(sc['demo_flow'])} flow steps")

    loaded = get_imagina_showcase(user_id)
    assert loaded is not None
    show_path = os.path.join(DATA_DIR, "showcase", user_id, "SHOWCASE_SUMMARY.md")
    assert os.path.exists(show_path)
    print("4. Showcase files exist")

    assert sc.get("latest_protocol", {}).get("title") is not None
    print("5. Latest protocol in showcase")

    assert sc.get("benchmark_summary", {}).get("avg_iqi_proxy") is not None
    print("6. Benchmark summary in showcase")

    assert sc.get("manifest", {}).get("protocol_hash") is not None
    print("7. Reproducibility manifest in showcase")

    manifest = build_release_manifest("V25")
    assert manifest.get("version") == "V25"
    assert len(manifest.get("implemented_modules", [])) >= 13
    print(f"8. Release manifest: {len(manifest['implemented_modules'])} modules")

    from app.core.imagery.showcase_aggregator import build_imagina_showcase as build
    _ = build(user_id)

    for f in (demo.get("files", []) if isinstance(demo.get("files"), list) else []):
        if os.path.exists(str(f)):
            c = open(str(f), errors="ignore").read().lower()
            assert "raw_eeg" not in c
    print("9. No raw EEG in showcase/export")

    assert sc.get("not_clinical") is True
    assert sc.get("not_bci_claim") is True
    assert manifest.get("not_mind_reading") is True
    print("10. Safety flags: All OK")

    print("\n=== V25 PUBLIC SHOWCASE DEMO: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

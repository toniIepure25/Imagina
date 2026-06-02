"""V27 Docker CI Release Pack — Integration Test."""

import os
import sys


def main():
    print("=== V27 DOCKER CI RELEASE PACK ===\n")
    user_id = "v27_release"

    from app.core.imagery.release_health import (
        build_imagina_architecture_map,
        build_imagina_submission_pack,
        build_imagina_technical_whitepaper,
        export_imagina_api_contract,
        generate_reviewer_demo_script,
        run_release_health_check,
    )
    h = run_release_health_check()
    assert h.get("release_candidate_ready") is True
    print("1. Release health: RC ready")

    c = export_imagina_api_contract()
    assert c.get("total_endpoints", 0) >= 30
    print("2. API contract exported")

    a = build_imagina_architecture_map()
    assert len(a.get("layers", [])) >= 7
    print("3. Architecture map built")

    ds = generate_reviewer_demo_script()
    assert len(ds.get("scripts_generated", [])) >= 3
    print("4. Demo scripts generated")

    w = build_imagina_technical_whitepaper()
    assert len(w.get("sections", [])) >= 8
    print("5. Whitepaper built")

    sp = build_imagina_submission_pack(user_id)
    assert sp.get("n_files", 0) >= 5
    print(f"6. Submission pack: {sp['n_files']} files")

    from app.cli.imagina_local_ci import validate_submission_pack
    v = validate_submission_pack(sp["submission_dir"])
    assert v.get("valid_submission_pack") is True
    print("7. Submission pack validates")

    from app.cli.imagina_local_ci import build_release_artifact_index
    idx = build_release_artifact_index(user_id)
    assert idx.get("n_existing", 0) >= 6
    print(f"8. Artifact index: {idx['n_existing']} existing, {idx['n_missing']} missing")

    from app.cli.imagina_local_ci import run_local_ci
    ci = run_local_ci("quick")
    assert ci.get("ci_run_id") is not None
    print(f"9. Local CI quick: duration={ci.get('duration_seconds',0):.0f}s")

    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    for f in ["docker-compose.release.yml", "backend/Dockerfile.release", "frontend/Dockerfile.release",
              "scripts/imagina_docker_smoke.sh"]:
        assert os.path.exists(os.path.join(repo, f)), f"Missing: {f}"
    print("10. Docker files exist")

    assert h.get("not_clinical") is True
    assert v.get("not_bci_claim") is True
    print("11. Safety flags: All OK")

    print("\n=== V27 DOCKER CI RELEASE PACK: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

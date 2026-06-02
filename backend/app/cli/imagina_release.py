"""IMAGINA V26 — Release Candidate CLI."""

import sys


def cmd_health():
    print("[IMAGINA RELEASE] Running health check...")
    from app.core.imagery.release_health import run_release_health_check
    result = run_release_health_check()
    print(f"  Status: {result['overall_status']}")
    print(f"  RC Ready: {result['release_candidate_ready']}")
    print(f"  Checks: {len(result.get('checks', []))}, Warnings: {len(result.get('warnings', []))}, Failures: {len(result.get('failures', []))}")
    return 0 if result["overall_status"] != "fail" else 1


def cmd_api_contract():
    print("[IMAGINA RELEASE] Exporting API contract...")
    from app.core.imagery.release_health import export_imagina_api_contract
    c = export_imagina_api_contract()
    print(f"  Groups: {len(c.get('groups', []))}, Endpoints: {c.get('total_endpoints', 0)}")
    return 0


def cmd_architecture():
    print("[IMAGINA RELEASE] Building architecture map...")
    from app.core.imagery.release_health import build_imagina_architecture_map
    a = build_imagina_architecture_map()
    print(f"  Layers: {len(a.get('layers', []))}")
    return 0


def cmd_demo_script():
    print("[IMAGINA RELEASE] Generating demo scripts...")
    from app.core.imagery.release_health import generate_reviewer_demo_script
    s = generate_reviewer_demo_script()
    print(f"  Scripts: {s.get('scripts_generated', [])}")
    return 0


def cmd_whitepaper():
    print("[IMAGINA RELEASE] Building technical whitepaper...")
    from app.core.imagery.release_health import build_imagina_technical_whitepaper
    w = build_imagina_technical_whitepaper()
    print(f"  Sections: {len(w.get('sections', []))}")
    return 0


def cmd_submission():
    user = sys.argv[3] if len(sys.argv) > 3 else "demo_user"
    print(f"[IMAGINA RELEASE] Building submission pack for {user}...")
    from app.core.imagery.release_health import build_imagina_submission_pack
    p = build_imagina_submission_pack(user)
    print(f"  Files: {p.get('n_files', 0)} at {p.get('submission_dir', '')}")
    return 0


def cmd_all():
    print("=" * 60 + "\n  IMAGINA V26 Release Candidate\n" + "=" * 60)
    import os
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    cmd_health()
    print()
    cmd_api_contract()
    print()
    cmd_architecture()
    print()
    cmd_demo_script()
    print()
    cmd_whitepaper()
    print()
    cmd_submission()
    print()
    print("=" * 60 + "\n  Release artifacts generated in data/imagina/\n" + "=" * 60)
    return 0


def cmd_verify():
    import os
    import subprocess
    bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    print("[IMAGINA RELEASE] Running verification...")
    tests = ["app.cli.imagina_v24_sdk_standard_test", "app.cli.imagina_v25_public_showcase_test"]
    for t in tests:
        r = subprocess.run([sys.executable, "-m", t], cwd=bd, capture_output=True)
        print(f"  [{'PASS' if r.returncode == 0 else 'FAIL'}] {t.split('_test')[0]}")
    from app.core.imagery.release_health import run_release_health_check
    h = run_release_health_check()
    print(f"  RC Ready: {h['release_candidate_ready']}")
    return 0


def main():
    cmds = {"health": cmd_health, "api-contract": cmd_api_contract, "architecture": cmd_architecture,
            "demo-script": cmd_demo_script, "whitepaper": cmd_whitepaper,
            "submission-pack": cmd_submission, "all": cmd_all, "verify": cmd_verify}
    if len(sys.argv) < 2:
        print("IMAGINA Release CLI: health | api-contract | architecture | demo-script | whitepaper | submission-pack | all | verify")
        return 0
    cmd = sys.argv[1]
    if cmd in cmds:
        return cmds[cmd]()
    print(f"Unknown: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

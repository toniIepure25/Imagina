"""IMAGINA V25 — One-Command Demo Bootstrap CLI."""

import sys


def cmd_seed():
    print("[IMAGINA DEMO] Seeding demo data...")
    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary, seed_imagina_demo_user
    demo = seed_imagina_demo_user("demo_user", reset_existing=True)
    build_portfolio_safe_summary("demo_user")
    print(f"  Protocol: {demo.get('created_protocol_id', '')[:12]}...")
    print(f"  Run: {demo.get('created_run_id', '')[:12]}...")
    print(f"  Sessions: {len(demo.get('created_sessions', []))}")
    print(f"  Export: {demo.get('export_dir', '')[:50]}...")
    print("[DONE] Demo data seeded.")
    return 0


def cmd_showcase():
    print("[IMAGINA DEMO] Building showcase...")
    from app.core.imagery.showcase_aggregator import build_imagina_showcase
    showcase = build_imagina_showcase("demo_user")
    import os
    sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                      "data", "imagina", "showcase", "demo_user", "SHOWCASE_SUMMARY.md")
    print(f"  Showcase: {showcase.get('showcase_id', '')[:12]}...")
    print(f"  Markdown: {sp}")
    print("  Frontend: http://localhost:3000/imagina/showcase")
    print("[DONE] Showcase built.")
    return 0


def cmd_full():
    print("=" * 60)
    print("  IMAGINA V25 — One-Command Demo Release")
    print("=" * 60)
    cmd_seed()
    print()
    cmd_showcase()
    print()
    from app.core.imagery.showcase_aggregator import build_release_manifest
    manifest = build_release_manifest("V25")
    print(f"  Release manifest: {manifest.get('release_id', '')[:12]}...")
    print()
    print("  === REVIEWER INSTRUCTIONS ===")
    print("  1. Start frontend: cd frontend && npm run dev")
    print("  2. Open showcase: http://localhost:3000/imagina/showcase")
    print("  3. Try SDK: cd backend && python3 -m app.cli.imagina_sdk schema")
    print("  4. Run tests: cd backend && python3 -m pytest app/tests/ -q")
    print("  5. Review: docs/IMAGINA_V*.md")
    print("=" * 60)
    return 0


def cmd_verify():
    import os
    import subprocess
    bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    print("[IMAGINA DEMO] Verifying...")
    tests = [
        "app.cli.imagina_v20_guided_session_runtime_test",
        "app.cli.imagina_v21_skill_tree_progression_test",
        "app.cli.imagina_v22_scene_simulator_test",
        "app.cli.imagina_v23_protocol_studio_test",
        "app.cli.imagina_v24_sdk_standard_test",
    ]
    for t in tests:
        r = subprocess.run([sys.executable, "-m", t], cwd=bd, capture_output=True)
        status = "PASS" if r.returncode == 0 else "FAIL"
        print(f"  [{status}] {t.split('_test')[0].replace('app.cli.', '')}")
    print("[DONE] Verification complete.")
    return 0


def main():
    if len(sys.argv) < 2:
        print("IMAGINA Demo CLI")
        print("  seed       — Seed demo user data")
        print("  showcase  — Build public showcase")
        print("  full      — seed + showcase + release manifest + instructions")
        print("  verify    — Run key tests")
        return 0
    cmds = {"seed": cmd_seed, "showcase": cmd_showcase, "full": cmd_full, "verify": cmd_verify}
    cmd = sys.argv[1]
    if cmd in cmds:
        return cmds[cmd]()
    print(f"Unknown: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

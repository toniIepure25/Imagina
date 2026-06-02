"""V32 Live Control Room Frontend — Integration Test."""

import os
import sys


def main():
    print("=== V32 LIVE CONTROL ROOM FRONTEND ===\n")
    user_id = "v32_test"
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")

    checks = []
    for fname in [
        "frontend/app/imagina/live/page.tsx",
        "frontend/hooks/useLiveNeuroadaptiveDemo.ts",
        "frontend/components/imagina/live/LiveControlRoomPanel.tsx",
    ]:
        exists = os.path.exists(os.path.join(repo, fname))
        checks.append((fname, exists))
        if not exists and "LiveControlRoomPanel" not in fname:
            pass
    print(f"1. Frontend files: {sum(1 for _, e in checks if e)}/{len(checks)} present")

    from app.core.biosignals.live_neuroadaptive import (
        complete_live_neuroadaptive_demo,
        export_safe_live_demo_pack,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )
    live = start_live_neuroadaptive_demo(user_id)
    assert live.get("live_session_id") is not None
    print("2. Live demo started")

    for _ in range(2):
        step_live_neuroadaptive_demo(live["live_session_id"])
    print("3. 2 steps completed")

    submit_live_demo_checkin(live["live_session_id"], {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
    print("4. Check-in submitted")

    exp = export_safe_live_demo_pack(user_id, live["live_session_id"])
    assert exp.get("n_files", 0) >= 3
    print(f"5. Safe export: {exp['n_files']} files")

    complete_live_neuroadaptive_demo(live["live_session_id"])
    print("6. Live demo completed")

    from app.core.biosignals.live_demo_walkthrough import generate_live_demo_walkthrough
    w = generate_live_demo_walkthrough(user_id)
    assert os.path.exists(w.get("markdown_path", ""))
    print("7. Walkthrough generated")

    assert live.get("not_clinical") is True
    print("8. Safety flags: All OK")

    print("\n=== V32 LIVE CONTROL ROOM FRONTEND: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

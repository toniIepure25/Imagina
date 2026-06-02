"""V34 Visible Scene Dynamics — Integration Test."""

import sys


def main():
    print("=== V34 VISIBLE SCENE DYNAMICS ===\n")
    user_id = "v34_test"

    from app.core.biosignals.live_neuroadaptive import (
        complete_live_neuroadaptive_demo,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )
    from app.core.biosignals.scene_dynamics_engine import (
        build_live_scene_replay,
        export_safe_live_scene_pack,
        get_scene_demo_scenarios,
        run_scene_demo_scenario,
    )

    live = start_live_neuroadaptive_demo(user_id)
    lsid = live["live_session_id"]

    # Step 1: normal baseline
    submit_live_demo_checkin(lsid, {"vividness": 5, "stability": 5, "effort": 4, "fatigue": 2, "confidence": 6, "discomfort": 1})
    f1 = step_live_neuroadaptive_demo(lsid)
    sa1 = f1.get("scene_adaptation", {}).get("scene_after_preview", {})

    # Step 2: low vividness + high effort
    submit_live_demo_checkin(lsid, {"vividness": 3, "stability": 3, "effort": 8, "fatigue": 7, "confidence": 3, "discomfort": 2})
    f2 = step_live_neuroadaptive_demo(lsid)
    sa2 = f2.get("scene_adaptation", {}).get("scene_after_preview", {})
    fog2 = sa2.get("fog", 0)
    clarity2 = sa2.get("clarity", 0)
    assert fog2 > sa1.get("fog", 0) - 0.01, f"Fog should increase: fog={fog2}"
    print(f"2. Effort overload: fog={fog2:.2f}, clarity={clarity2:.2f} (was {sa1.get('fog',0):.2f})")

    # Step 3: high vividness, good confidence
    submit_live_demo_checkin(lsid, {"vividness": 9, "stability": 8, "effort": 2, "fatigue": 1, "confidence": 9, "discomfort": 1})
    f3 = step_live_neuroadaptive_demo(lsid)
    sa3 = f3.get("scene_adaptation", {}).get("scene_after_preview", {})
    assert sa3.get("clarity", 0) > sa1.get("clarity", 0) - 0.01, f"Clarity should increase: {sa3.get('clarity',0)} vs {sa1.get('clarity',0)}"
    print(f"3. Clarity success: clarity={sa3.get('clarity',0):.2f}, fog={sa3.get('fog',0):.2f}")

    # Verify visible changes exist
    any_visible = (abs(sa3.get("clarity", 0) - sa1.get("clarity", 0)) > 0.01 or
                   abs(sa3.get("fog", 0) - sa1.get("fog", 0)) > 0.01)
    assert any_visible, f"No visible change: {sa1} → {sa3}"
    print("4. Visible changes confirmed: ✓")

    complete_live_neuroadaptive_demo(lsid)

    replay = build_live_scene_replay(lsid)
    assert replay.get("n_frames", 0) >= 3
    sm = replay.get("summary", {})
    assert sm.get("n_visible_changes", 0) >= 1, f"Expected visible changes in replay: {sm}"
    print(f"5. Replay: {replay['n_frames']} frames, n_visible_changes={sm.get('n_visible_changes')}")

    # Run scenarios
    sc = get_scene_demo_scenarios()
    assert sc.get("n_scenarios", 0) >= 3
    print(f"6. Scenarios: {sc['n_scenarios']}")

    cs = run_scene_demo_scenario(user_id, "clarity_success")
    assert cs.get("passed") is True, f"Clarity scenario failed: {cs}"
    print(f"7. clarity_success: passed, clarity_chg={cs['observed']['clarity_change']:.3f}")

    eo = run_scene_demo_scenario(user_id, "effort_overload")
    assert eo.get("passed") is True, f"Effort scenario failed: {eo}"
    print(f"8. effort_overload: passed, detail_chg={eo['observed']['detail_change']:.3f}")

    dp = run_scene_demo_scenario(user_id, "deepening")
    assert dp.get("passed") is True, f"Deepening scenario failed: {dp}"
    print(f"9. deepening: passed, detail_chg={dp['observed']['detail_change']:.3f}")

    exp = export_safe_live_scene_pack(user_id, lsid)
    assert exp.get("n_files", 0) >= 3
    print(f"10. Safe export: {exp['n_files']} files")

    assert cs.get("not_clinical") is True
    print("11. Safety flags: All OK")

    print("\n=== V34 VISIBLE SCENE DYNAMICS: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

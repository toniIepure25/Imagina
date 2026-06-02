"""V33 Closed-Loop Scene Adaptation — Integration Test."""

import os
import sys


def main():
    print("=== V33 CLOSED-LOOP SCENE ADAPTATION ===\n")
    user_id = "v33_test"

    from app.core.biosignals.live_neuroadaptive import (
        complete_live_neuroadaptive_demo,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )
    from app.core.biosignals.live_scene_adaptation import (
        build_live_scene_replay,
        export_safe_live_scene_pack,
        get_latest_live_scene_adaptation,
        get_live_scene_replay,
    )

    live = start_live_neuroadaptive_demo(user_id)
    lsid = live["live_session_id"]
    print(f"1. Live demo: {lsid[:12]}...")

    # Step 1: normal check-in
    submit_live_demo_checkin(lsid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
    f1 = step_live_neuroadaptive_demo(lsid)
    sa1 = f1.get("scene_adaptation", {})
    assert sa1.get("scene_after_preview") is not None
    sp1 = sa1["scene_after_preview"]
    for k in ["clarity", "fog", "motion_speed", "detail_density"]:
        assert 0 <= sp1.get(k, 0) <= 1
    print(f"2. Step 1 scene: clarity={sp1.get('clarity',0):.2f}, fog={sp1.get('fog',0):.2f}")

    # Step 2: low vividness, high effort
    submit_live_demo_checkin(lsid, {"vividness": 3, "stability": 3, "effort": 8, "fatigue": 6, "confidence": 4, "discomfort": 2})
    f2 = step_live_neuroadaptive_demo(lsid)
    sa2 = f2.get("scene_adaptation", {})
    sp2 = sa2["scene_after_preview"]
    print(f"3. Step 2 scene: clarity={sp2.get('clarity',0):.2f}, fog={sp2.get('fog',0):.2f} (effort/fatigue)")

    # Step 3: high vividness, good confidence
    submit_live_demo_checkin(lsid, {"vividness": 9, "stability": 8, "effort": 3, "fatigue": 2, "confidence": 9, "discomfort": 1})
    f3 = step_live_neuroadaptive_demo(lsid)
    sa3 = f3.get("scene_adaptation", {})
    sp3 = sa3["scene_after_preview"]
    print(f"4. Step 3 scene: clarity={sp3.get('clarity',0):.2f}, fog={sp3.get('fog',0):.2f} (high vividness)")

    # Verify scene frames persisted
    latest = get_latest_live_scene_adaptation(lsid)
    assert latest is not None
    assert latest.get("preview_only") is True
    print(f"5. Latest scene adaptation: preview_only={latest['preview_only']}")

    complete_live_neuroadaptive_demo(lsid)

    replay = build_live_scene_replay(lsid)
    assert replay.get("n_frames", 0) >= 3
    sm = replay.get("summary", {})
    assert sm.get("clarity_change") is not None
    print(f"6. Replay: {replay['n_frames']} frames, clarity_chg={sm['clarity_change']:.3f}, fog_chg={sm['fog_change']:.3f}")

    loaded_replay = get_live_scene_replay(lsid)
    assert loaded_replay is not None
    print("7. Replay persistent")

    exp = export_safe_live_scene_pack(user_id, lsid)
    assert exp.get("n_files", 0) >= 3
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"8. Safe scene export: {exp['n_files']} files, no raw EEG")

    assert latest.get("not_clinical") is True
    assert replay.get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V33 CLOSED-LOOP SCENE ADAPTATION: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

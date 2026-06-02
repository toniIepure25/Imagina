"""V31 Live Neuroadaptive Control Room — Integration Test."""

import os
import sys


def main():
    print("=== V31 LIVE NEUROADAPTIVE CONTROL ROOM ===\n")
    user_id = "v31_test"

    from app.core.biosignals.live_neuroadaptive import (
        build_live_control_room_summary,
        complete_live_neuroadaptive_demo,
        export_safe_live_demo_pack,
        get_live_event_schema,
        get_recent_live_events,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )

    schema = get_live_event_schema()
    assert len(schema.get("event_types", [])) >= 10
    print(f"1. Event schema: {len(schema['event_types'])} types")

    live = start_live_neuroadaptive_demo(user_id)
    lsid = live["live_session_id"]
    assert live.get("guided_session_id") is not None
    assert live.get("feed_id") is not None
    print(f"2. Live demo started: {lsid[:12]}...")

    for i in range(3):
        frame = step_live_neuroadaptive_demo(lsid)
        assert frame.get("sqi") is not None
        assert frame.get("adaptive_state") is not None
        assert frame.get("policy_action") is not None
    print("3. 3 live steps completed")

    submit_live_demo_checkin(lsid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
    print("4. Live check-in submitted")

    events = get_recent_live_events(user_id)
    assert len(events) >= 6, f"Only {len(events)} events"
    print(f"5. Event bus: {len(events)} events")

    summary = build_live_control_room_summary(user_id)
    assert summary.get("n_events", 0) >= 6
    print(f"6. Control room summary: {summary['n_events']} events, latest_state={summary.get('latest_adaptive_state', '')}")

    exp = export_safe_live_demo_pack(user_id, lsid)
    assert exp.get("n_files", 0) >= 3
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"7. Safe live export: {exp['n_files']} files, no raw EEG")

    done = complete_live_neuroadaptive_demo(lsid)
    assert done.get("status") == "completed"
    print("8. Live demo completed")

    assert frame.get("not_clinical") is True
    assert events[0].get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V31 LIVE NEUROADAPTIVE CONTROL ROOM: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

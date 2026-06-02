"""V29 Realtime Biosignal Dashboard — Integration Test."""

import os
import sys


def main():
    print("=== V29 REALTIME BIOSIGNAL DASHBOARD ===\n")
    user_id = "v29_test"

    from app.core.biosignals.biosignal_module import create_simulated_eeg_source
    create_simulated_eeg_source()

    from app.core.imagery.guided_session_runtime import (
        advance_guided_session_phase,
        complete_guided_session,
        start_guided_imagery_session,
        submit_guided_micro_checkin,
    )
    gs = start_guided_imagery_session(user_id, "red_circle_vividness", "manual",
                                       biosignal_source_id="simulated_eeg")
    sid = gs["session_id"]
    mid = gs.get("biosignal_monitor_id", "")
    msid = gs.get("biosignal_marker_session_id", "")
    print(f"1. Session started with biosignal: monitor={mid[:12]}...")

    from app.core.biosignals.biosignal_dashboard import (
        build_biosignal_dashboard_summary,
        build_biosignal_event_timeline,
        create_realtime_feed_session,
        evaluate_signal_quality_gate,
        export_safe_biosignal_pack,
        get_realtime_feed_summary,
        poll_realtime_feed,
        stop_realtime_feed,
    )

    feed = create_realtime_feed_session(sid)
    fid = feed["feed_id"]
    print(f"2. Feed started: {fid[:12]}...")

    advance_guided_session_phase(sid)
    submit_guided_micro_checkin(sid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})

    for _ in range(3):
        f = poll_realtime_feed(fid)
        assert f.get("raw_samples_included") is False
    print("3. 3 frames polled, raw_samples_included=False")

    sq = evaluate_signal_quality_gate({"overall_sqi": 0.85, "quality_state": "good"})
    assert sq.get("gate_state") in ("open", "caution", "degraded", "blocked")
    print(f"4. Quality gate: {sq['gate_state']}")

    complete_guided_session(sid)
    stop_realtime_feed(fid)

    tl = build_biosignal_event_timeline(sid, mid, msid)
    assert tl.get("n_events", 0) >= 1
    print(f"5. Timeline: {tl['n_events']} events")

    dash = build_biosignal_dashboard_summary(user_id)
    assert dash.get("sources") is not None
    print(f"6. Dashboard: {len(dash.get('sources', []))} sources")

    fs = get_realtime_feed_summary(fid)
    assert fs.get("n_frames", 0) >= 3
    print(f"7. Feed summary: {fs['n_frames']} frames, avg_sqi={fs.get('avg_sqi', 0):.2f}")

    exp = export_safe_biosignal_pack(user_id, sid)
    assert exp.get("n_files", 0) >= 4
    all_ok = True
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        if any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"]):
            all_ok = False
    assert all_ok
    print(f"8. Safe export: {exp['n_files']} files, no raw EEG")

    assert f.get("not_clinical") is True
    assert tl.get("not_bci_claim") is True
    assert dash.get("not_neurofeedback_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V29 REALTIME BIOSIGNAL DASHBOARD: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

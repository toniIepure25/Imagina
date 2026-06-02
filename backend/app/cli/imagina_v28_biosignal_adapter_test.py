"""V28 Biosignal Adapter Sandbox — Integration Test."""

import sys


def main():
    print("=== V28 BIOSIGNAL ADAPTER SANDBOX ===\n")

    from app.core.biosignals.biosignal_module import (
        build_biosignal_session_report,
        check_brainflow_available,
        close_marker_session,
        compute_signal_quality,
        create_simulated_eeg_source,
        discover_lsl_streams,
        list_biosignal_sources,
        list_markers,
        read_simulated_window,
        record_marker,
        sample_biosignal_monitor,
        stop_biosignal_monitor,
    )

    src = create_simulated_eeg_source()
    assert src.get("source_id") == "simulated_eeg"
    assert src.get("source_type") == "simulated"
    print("1. Simulated source created")

    sources = list_biosignal_sources()
    assert "simulated_eeg" in sources
    print("2. Registry lists source")

    window = read_simulated_window()
    assert window.get("raw_samples_included") is False
    assert window.get("n_samples", 0) > 0
    print(f"3. Window: {window['n_samples']} samples, raw_included=False")

    sq = compute_signal_quality(window.get("window_summary", {}))
    assert sq.get("overall_sqi", -1) >= 0
    assert sq.get("quality_state") in ("excellent", "good", "usable", "poor", "unusable")
    print(f"4. Signal quality: SQI={sq['overall_sqi']:.2f}, state={sq['quality_state']}")

    lsl = discover_lsl_streams()
    assert lsl.get("available") is False or lsl.get("available") is True
    print(f"5. LSL: available={lsl.get('available')}, reason={lsl.get('reason', 'ok')}")

    bf = check_brainflow_available()
    assert "available" in bf
    print(f"6. BrainFlow: available={bf.get('available')}")

    from app.core.imagery.guided_session_runtime import (
        advance_guided_session_phase,
        complete_guided_session,
        start_guided_imagery_session,
        submit_guided_micro_checkin,
    )
    user_id = "v28_test"
    gs = start_guided_imagery_session(user_id, "red_circle_vividness", "manual",
                                       biosignal_source_id="simulated_eeg")
    sid = gs["session_id"]
    assert gs.get("biosignal_monitor_id") is not None
    mid = gs["biosignal_monitor_id"]
    print(f"7. Session with biosignal: monitor={mid[:12]}...")

    msid = gs.get("biosignal_marker_session_id")
    assert msid is not None
    record_marker(msid, "phase_started", {"phase": "preparation"})
    markers = list_markers(msid)
    assert len(markers) >= 1
    print(f"8. Marker sync: {len(markers)} markers")

    advance_guided_session_phase(sid)
    submit_guided_micro_checkin(sid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
    sample = sample_biosignal_monitor(mid)
    assert sample.get("raw_samples_included") is False
    print(f"9. Monitor sample: raw_included=False, SQI={sample['signal_quality'].get('overall_sqi', 0):.2f}")

    complete_guided_session(sid)
    summ = stop_biosignal_monitor(mid)
    assert summ.get("n_derived_samples", 0) >= 1
    assert summ.get("raw_eeg_included") is False
    print(f"10. Monitor stopped: {summ['n_derived_samples']} samples, avg_sqi={summ.get('avg_sqi', 0):.2f}")

    close_marker_session(msid)

    report = build_biosignal_session_report(sid)
    assert report.get("raw_eeg_included") is False
    print("11. Biosignal report: raw_eeg_included=False")

    assert window.get("not_clinical") is True
    assert sq.get("not_bci_claim") is True
    assert report.get("not_neurofeedback_claim") is True
    print("12. Safety flags: All OK")

    print("\n=== V28 BIOSIGNAL ADAPTER SANDBOX: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""V30 Multimodal Fusion — Integration Test."""

import os
import sys


def main():
    print("=== V30 MULTIMODAL FUSION SANDBOX ===\n")
    user_id = "v30_test"

    from app.core.biosignals.biosignal_module import create_simulated_eeg_source
    create_simulated_eeg_source()

    from app.core.imagery.guided_session_runtime import (
        complete_guided_session,
        start_guided_imagery_session,
        submit_guided_micro_checkin,
    )
    gs = start_guided_imagery_session(user_id, "red_circle_vividness", "manual",
                                       biosignal_source_id="simulated_eeg")
    sid = gs["session_id"]

    from app.core.biosignals.biosignal_dashboard import create_realtime_feed_session, poll_realtime_feed
    feed = create_realtime_feed_session(sid)

    for _ in range(2):
        poll_realtime_feed(feed["feed_id"])
    submit_guided_micro_checkin(sid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})

    from app.core.biosignals.fusion_multimodal import (
        apply_neuroadaptive_policy,
        build_fusion_session_summary,
        build_multimodal_observation,
        estimate_adaptive_state,
        export_safe_fusion_pack,
        recommend_neuroadaptive_policy,
        run_single_fusion_step,
    )

    obs = build_multimodal_observation(sid, feed["feed_id"], user_id)
    assert obs.get("data_completeness", -1) > 0
    print(f"1. Observation: completeness={obs['data_completeness']:.2f}")

    state = estimate_adaptive_state(obs)
    allowed = ["ready", "stable_practice", "deepening", "clarity_building", "fatigue_risk",
               "effort_overload", "discomfort_warning", "signal_degraded", "signal_blocked",
               "pause_recommended", "recovery_mode", "insufficient_data"]
    assert state["state"] in allowed, f"Unknown state: {state['state']}"
    assert 0 <= state["confidence"] <= 1
    print(f"2. State: {state['state']}, confidence={state['confidence']:.2f}")

    policy = recommend_neuroadaptive_policy(state, obs)
    allowed_actions = ["continue_current_task", "increase_scene_clarity", "reduce_visual_complexity",
                       "slow_guidance_pace", "suggest_short_pause", "switch_to_recovery_protocol",
                       "lower_difficulty_next_block", "keep_biosignal_dashboard_visible_only",
                       "hide_derived_biosignal_metrics", "request_manual_checkin", "stop_session_safely"]
    assert policy["recommended_action"] in allowed_actions
    print(f"3. Policy: {policy['recommended_action']}")

    app = apply_neuroadaptive_policy(sid, policy)
    assert app.get("mode") == "preview"
    print(f"4. Application: mode={app['mode']}, requires_confirmation={app.get('requires_user_confirmation')}")

    step = run_single_fusion_step(user_id, sid, feed["feed_id"])
    assert step.get("observation") is not None
    assert step.get("adaptive_state") is not None
    assert step.get("policy") is not None
    print("5. Fusion step: observation + state + policy + application")

    complete_guided_session(sid)

    summary = build_fusion_session_summary(user_id, sid)
    assert summary.get("n_fusion_steps", 0) >= 1
    print(f"6. Fusion summary: {summary['n_fusion_steps']} steps, states={summary.get('state_distribution', {})}")

    exp = export_safe_fusion_pack(user_id, sid)
    assert exp.get("n_files", 0) >= 2
    for fp in exp.get("files", []):
        fn = os.path.basename(str(fp)).lower()
        assert not any(fn.endswith(ext) for ext in [".edf", ".fif", ".bdf"])
    print(f"7. Safe fusion export: {exp['n_files']} files, no raw EEG")

    assert obs.get("not_clinical") is True
    assert state.get("not_bci_claim") is True
    assert policy.get("not_neurofeedback_claim") is True
    print("8. Safety flags: All OK")

    print("\n=== V30 MULTIMODAL FUSION SANDBOX: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

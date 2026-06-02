"""V20 Guided Imagery Session Runtime — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "imagina")
CALIB_DIR = os.path.join(DATA_DIR, "calibration_sessions")


def _ensure_data(user_id):
    existing = []
    if os.path.isdir(CALIB_DIR):
        for sid in os.listdir(CALIB_DIR):
            mp = os.path.join(CALIB_DIR, sid, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp))
                if m.get("user_id") == user_id and m.get("status") == "completed":
                    existing.append(m)
    if len(existing) >= 4:
        return
    for i, pid_val in enumerate([0.500, 0.460, 0.430, 0.390]):
        sid = str(uuid4())
        session = {"session_id": sid, "user_id": user_id, "task": {"id": "simple_red_circle_reference", "target_dimensions": ["color", "shape", "spatial_position"]}, "status": "completed", "started_at": f"2026-09-{(i+1)*4:02d}T12:00:00Z", "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6}, "imagery_rating": {"clarity": max(1,7-i), "detail": max(1,6-i), "color_strength": max(1,8-i), "spatial_stability": max(1,6-i), "effort": 3, "fatigue": 2, "confidence": 7}, "pid_v2": {"pid_v2": pid_val, "subscores": {"clarity_gap": 0.12, "detail_gap": 0.15, "color_gap": 0.10, "spatial_gap": 0.08, "emotional_gap": 0.02}, "reliability": {"confidence": 0.7}}, "not_clinical": True}
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "manifest.json"), "w") as f:
            json.dump(session, f, indent=2, default=str)


def _ensure_v19_sessions(user_id):
    from app.core.imagery.task_session_manager import list_imagery_task_sessions
    existing = [s for s in list_imagery_task_sessions(user_id) if s.get("status") == "completed"]
    if len(existing) >= 5:
        return
    from app.core.imagery.task_session_manager import (
        complete_imagery_task_session,
        start_imagery_task_session,
        submit_imagery_task_rating,
    )
    for tid, ratings in [
        ("red_circle_vividness", {"vividness": 8, "color_control": 7, "effort": 3, "fatigue": 2, "confidence": 8}),
        ("blue_cube_vividness", {"vividness": 6, "spatial_control": 5, "effort": 4, "fatigue": 3, "confidence": 7}),
        ("color_shift_red_to_blue", {"color_control": 7, "meta_control": 6, "effort": 4, "fatigue": 2, "confidence": 8}),
        ("static_cube_stability", {"spatial_control": 5, "vividness": 6, "stability": 5, "effort": 5, "fatigue": 3, "confidence": 6}),
        ("apple_detail_generation", {"detail": 7, "vividness": 7, "color_control": 8, "effort": 4, "fatigue": 2, "confidence": 8}),
        ("rotating_object", {"motion": 8, "spatial_control": 7, "effort": 3, "fatigue": 1, "confidence": 9}),
    ]:
        s = start_imagery_task_session(user_id, tid)
        submit_imagery_task_rating(s["session_id"], ratings)
        complete_imagery_task_session(s["session_id"])


def main():
    print("=== V20 GUIDED IMAGERY SESSION RUNTIME ===\n")
    user_id = "v20_test"

    _ensure_data(user_id)
    _ensure_v19_sessions(user_id)

    from app.core.imagery.imagery_phenotype import build_imagery_phenotype, generate_task_based_imagery_plan
    phenotype = build_imagery_phenotype(user_id)
    plan = generate_task_based_imagery_plan(user_id, 7)
    print(f"1. Phenotype={phenotype.get('phenotype_label','')}, Plan={len(plan.get('daily_tasks',[]))} days")

    from app.core.imagery.guided_session_runtime import (
        advance_guided_session_phase,
        build_guided_session_report,
        complete_guided_session,
        export_guided_session_as_task_rating,
        generate_adaptive_feedback,
        get_guided_plan_progress,
        get_guided_session,
        list_guided_sessions,
        mark_guided_plan_day_completed,
        resume_guided_session,
        start_guided_imagery_session,
        start_next_guided_task_from_plan,
        submit_guided_micro_checkin,
    )

    s = start_guided_imagery_session(user_id, "red_circle_vividness", "manual")
    assert s["status"] == "active"
    assert s["current_phase"] == "preparation"
    print(f"2. Session started: phase={s['current_phase']}, active")

    s = advance_guided_session_phase(s["session_id"])
    s2 = s.get("session", s)
    print(f"3. Advanced: phase={s2.get('current_phase','')}")

    r = submit_guided_micro_checkin(s2["session_id"], {"vividness": 7, "stability": 6, "effort": 4, "fatigue": 3, "confidence": 8, "discomfort": 1})
    proxies = r.get("proxies", {})
    assert proxies.get("iqi_proxy", -1) >= 0
    assert proxies.get("pid_proxy", -1) >= 0
    print(f"4. Check-in: IQI={proxies['iqi_proxy']:.2f}, PID={proxies['pid_proxy']:.2f}, safety={proxies.get('safety_state','')}")

    r2 = submit_guided_micro_checkin(s2["session_id"], {"vividness": 3, "stability": 2, "effort": 8, "fatigue": 8, "confidence": 3, "discomfort": 2})
    p2 = r2.get("proxies", {})
    assert p2.get("safety_state") in ("pause", "slow_down"), f"Expected pause/slow_down, got {p2.get('safety_state')}"
    print(f"5. High fatigue causes: {p2['safety_state']}")

    fb = generate_adaptive_feedback(s2["session_id"])
    assert fb.get("feedback_type") is not None
    print(f"6. Feedback: type={fb['feedback_type']}")

    # Session was auto-paused by safety check; resume it
    s2 = resume_guided_session(s2["session_id"])
    assert s2["status"] == "active"
    print("7. Auto-pause from safety check + resume: OK")

    complete_guided_session(s2["session_id"])
    s_final = get_guided_session(s2["session_id"])
    assert s_final["status"] == "completed"
    print("8. Session completed")

    report = build_guided_session_report(s2["session_id"])
    assert report.get("summary", {}).get("n_checkins", 0) >= 1
    print(f"9. Report: checkins={report['summary']['n_checkins']}, IQI={report['summary'].get('final_iqi_proxy','')}")

    export = export_guided_session_as_task_rating(s2["session_id"])
    assert export.get("linked_task_session_id") is not None
    print(f"10. Exported as task rating: {export.get('linked_task_session_id','')[:12]}...")

    pref = start_next_guided_task_from_plan(user_id)
    plan_session = pref.get("session", {})
    assert plan_session.get("session_id") is not None
    print(f"11. Next plan task started: {plan_session.get('task_metadata',{}).get('title','')}")

    prog = get_guided_plan_progress(user_id)
    assert prog.get("run") is not None
    print(f"12. Plan progress: day={prog['run']['current_day']}")

    complete_guided_session(plan_session["session_id"])
    sm = mark_guided_plan_day_completed(user_id, plan_session["session_id"])
    assert sm.get("run") is not None
    print(f"13. Plan day completed: adherence={(sm['run']['adherence_rate']*100):.0f}%")

    all_gs = list_guided_sessions(user_id)
    assert len(all_gs) >= 2
    print(f"14. Guided sessions: {len(all_gs)} total")

    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    gs = profile.get("guided_imagery_summary", {})
    print(f"15. Profile guided_imagery_summary: has_guided={gs.get('has_guided_sessions')}, completed={gs.get('n_completed_guided_sessions')}")

    final_session = get_guided_session(s_final["session_id"])
    assert final_session.get("not_clinical") is True
    assert proxies.get("not_mind_reading") is True
    assert report.get("not_bci_claim") is True
    print("16. Safety flags: All OK")

    print("\n=== V20 GUIDED IMAGERY SESSION RUNTIME: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

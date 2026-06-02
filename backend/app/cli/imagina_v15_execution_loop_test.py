"""V15 Adaptive Plan Execution — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "imagina")
CALIB_DIR = os.path.join(DATA_DIR, "calibration_sessions")


def ensure_calibration_sessions_for(user_id="v15_test"):
    d = CALIB_DIR
    existing = []
    if os.path.isdir(d):
        for sid in os.listdir(d):
            mp = os.path.join(d, sid, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp))
                if m.get("user_id") == user_id and m.get("status") == "completed":
                    existing.append(m)

    if len(existing) >= 2:
        return [s for s in sorted(existing, key=lambda x: x.get("started_at", ""))]

    pid_values = [0.600, 0.550, 0.490, 0.430]
    for i, pid_val in enumerate(pid_values):
        sid = str(uuid4())
        session = {
            "session_id": sid, "user_id": user_id,
            "task": {"id": "simple_red_circle_reference",
                     "target_dimensions": ["color", "shape", "spatial_position"]},
            "status": "completed",
            "started_at": f"2026-06-{(i+1)*5:02d}T12:00:00Z",
            "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6},
            "imagery_rating": {
                "clarity": max(1, 6 - i), "detail": max(1, 5 - i),
                "color_strength": max(1, 7 - i), "spatial_stability": max(1, 5 - i),
                "effort": 4 - i * 0.2, "fatigue": 3 + i * 0.3, "confidence": 7 - i * 0.3,
                "reconstruction_similarity": 7,
            },
            "pid_v2": {
                "pid_v2": pid_val,
                "perception_similarity_score": round(1.0 - pid_val, 3),
                "subscores": {
                    "clarity_gap": 0.180, "detail_gap": 0.220,
                    "color_gap": 0.160, "spatial_gap": 0.140, "emotional_gap": 0.050,
                },
                "reliability": {"confidence": 0.7, "reason": ""},
                "interpretation": "Test calibration",
                "analysis_mode": "personal_exploratory_training",
                "not_clinical": True,
            },
        }
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "manifest.json"), "w") as f:
            json.dump(session, f, indent=2, default=str)
    sessions_built = []
    for sid in os.listdir(d):
        mp = os.path.join(d, sid, "manifest.json")
        if os.path.exists(mp):
            m = json.load(open(mp))
            if m.get("user_id") == user_id and m.get("status") == "completed":
                sessions_built.append(m)
    return sorted(sessions_built, key=lambda x: x.get("started_at", ""))


def main():
    print("=== V15 ADAPTIVE PLAN EXECUTION ===\n")

    user_id = "v15_test"

    # 1. Ensure calibration sessions + adaptive plan
    sessions = ensure_calibration_sessions_for(user_id)
    print(f"1. Calibration sessions: {len(sessions)}")

    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    plan = build_adaptive_training_plan(user_id)
    assert plan.get("status") != "insufficient_data", f"Plan failed: {plan}"
    print(f"   Plan: {plan['plan_title']} (focus={plan['training_focus']})")

    # 2. Start execution
    from app.core.adaptive.adaptive_plan_execution import (
        attach_calibration_to_execution_day,
        close_plan_execution,
        complete_execution_day,
        list_plan_executions,
        start_plan_execution,
    )

    ex = start_plan_execution(user_id)
    assert "error" not in ex, f"Start failed: {ex}"
    eid = ex["execution_id"]
    assert ex["status"] == "active"
    assert len(ex["days"]) == 7
    print(f"2. Execution started: {eid[:12]}...")

    # 3. Duplicate start protection
    dup = start_plan_execution(user_id)
    assert "error" in dup, f"Should block duplicate: {dup}"
    print("3. Duplicate execution blocked: OK")

    # 4. Complete day 1 (checkpoint day)
    checkin1 = {"completed": True, "duration_minutes_actual": 10,
                "difficulty_rating": 5, "clarity_rating": 7,
                "fatigue_rating": 2, "focus_quality": 8, "notes": "Clear session."}
    ex = complete_execution_day(user_id, eid, 1, checkin1)
    assert ex["days"][0]["status"] == "completed"
    print(f"4. Day 1 completed: {ex['days'][0]['status']}")

    # 5. Attach calibration to day 1 checkpoint
    from app.core.calibration.pid_v2_calibration import (
        start_calibration_session,
        submit_imagery_rating,
        submit_reference_rating,
    )
    cal = start_calibration_session(user_id, "simple_red_circle_reference")
    cal_sid = cal["session_id"]
    submit_reference_rating(cal_sid, {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal_sid, {"clarity": 7, "detail": 6, "color_strength": 8, "spatial_stability": 6,
                                     "effort": 3, "fatigue": 2, "confidence": 8, "reconstruction_similarity": 7})
    ex = attach_calibration_to_execution_day(user_id, eid, 1, cal_sid)
    assert ex["days"][0].get("checkpoint_pid") is not None
    print(f"5. Day 1 calibration attached: PID={ex['days'][0]['checkpoint_pid']}")

    # 6. Complete day 2
    checkin2 = {"completed": True, "duration_minutes_actual": 12,
                "difficulty_rating": 6, "clarity_rating": 6,
                "fatigue_rating": 4, "focus_quality": 7}
    ex = complete_execution_day(user_id, eid, 2, checkin2)
    assert ex["days"][1]["status"] == "completed"
    print("6. Day 2 completed")

    # 7. Skip day 3
    ex = complete_execution_day(user_id, eid, 3, {"completed": False})
    assert ex["days"][2]["status"] == "skipped"
    print("7. Day 3 skipped")

    # 8. Complete day 4 (checkpoint day) with calibration
    ex = complete_execution_day(user_id, eid, 4, {
        "completed": True, "duration_minutes_actual": 10,
        "difficulty_rating": 4, "clarity_rating": 8,
        "fatigue_rating": 3, "focus_quality": 8,
    })

    cal2 = start_calibration_session(user_id, "simple_red_circle_reference")
    cal2_sid = cal2["session_id"]
    submit_reference_rating(cal2_sid, {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal2_sid, {"clarity": 8, "detail": 7, "color_strength": 8, "spatial_stability": 7,
                                      "effort": 3, "fatigue": 2, "confidence": 9, "reconstruction_similarity": 8})
    ex = attach_calibration_to_execution_day(user_id, eid, 4, cal2_sid)
    assert ex["days"][3].get("checkpoint_pid") is not None
    print(f"8. Day 4 calibration attached: PID={ex['days'][3]['checkpoint_pid']}")

    # 9. Invalid day protection
    err = complete_execution_day(user_id, eid, 1, {"completed": False})
    assert "error" in err, f"Should reject re-completion: {err}"
    print("9. Re-completion rejected: OK")

    # 10. Close execution
    ex = close_plan_execution(user_id, eid)
    assert ex["status"] == "completed"
    assert ex["completed_at"] is not None
    assert ex["summary"]["completed_days"] == 3
    print(f"10. Execution closed: completed={ex['summary']['completed_days']}, skipped={ex['summary']['skipped_days']}")

    # 11. Execution analytics
    from app.core.adaptive.adaptive_execution_analytics import analyze_all_executions, analyze_plan_execution
    analysis = analyze_plan_execution(user_id, eid)
    assert analysis.get("response_category") is not None
    assert round(analysis.get("adherence", {}).get("adherence_rate", 0), 2) == round(3/7, 2)
    assert analysis.get("pid_checkpoint_analysis", {}).get("baseline_pid") is not None
    print(f"11. Execution analysis: adherence={analysis['adherence']['adherence_rate']:.2f}, response={analysis['response_category']}")
    print(f"    PID: {analysis['pid_checkpoint_analysis'].get('baseline_pid')} -> {analysis['pid_checkpoint_analysis'].get('final_pid')}")
    print(f"    Interpretation: {analysis.get('interpretation', '')[:60]}...")

    # 12. All executions analysis
    all_a = analyze_all_executions(user_id)
    assert all_a.get("n_executions", 0) >= 1
    print(f"12. All executions: n={all_a['n_executions']}, avg_adherence={all_a.get('average_adherence', 0):.2f}")

    # 13. Longitudinal progress report
    from app.core.adaptive.longitudinal_progress_report import generate_longitudinal_progress_report
    report = generate_longitudinal_progress_report(user_id)
    assert report.get("summary", {}).get("n_executions", 0) >= 1
    assert report.get("timeline") is not None
    print(f"13. Longitudinal report: calibrations={report['summary']['n_calibration_sessions']}, executions={report['summary']['n_executions']}")
    print(f"    Timeline events: {len(report.get('timeline', []))}")

    # 14. Personal profile with execution summary
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    exec_summary = profile.get("execution_summary", {})
    assert exec_summary.get("latest_execution_id") is not None, f"No execution summary: {exec_summary}"
    print(f"14. Profile execution_summary: id={exec_summary.get('latest_execution_id', '')[:12]}...")

    # 15. List executions
    executions = list_plan_executions(user_id)
    assert len(executions) >= 1
    print(f"15. Execution list: {len(executions)} execution(s)")

    # 16. Safety flags
    assert ex.get("not_clinical") is True
    assert analysis.get("not_mind_reading") is True
    assert report.get("not_bci_claim") is True
    assert report.get("production_valid") is False
    print("16. Safety flags: All OK")

    # 17. Sparse user
    from app.core.adaptive.adaptive_plan_execution import get_latest_plan_execution as get_latest
    assert get_latest("nonexistent_v15") is None
    sparse_analysis = analyze_all_executions("nonexistent_v15")
    assert sparse_analysis.get("n_executions") == 0
    print("17. Sparse user: Handled")

    print("\n=== V15 ADAPTIVE PLAN EXECUTION: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

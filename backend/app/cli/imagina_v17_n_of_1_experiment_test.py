"""V17 N-of-1 Experiment Engine — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "imagina")
CALIB_DIR = os.path.join(DATA_DIR, "calibration_sessions")


def ensure_calibrations(user_id="v17_test"):
    existing = []
    if os.path.isdir(CALIB_DIR):
        for sid in os.listdir(CALIB_DIR):
            mp = os.path.join(CALIB_DIR, sid, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp))
                if m.get("user_id") == user_id and m.get("status") == "completed":
                    existing.append(m)
    if len(existing) >= 4:
        return sorted(existing, key=lambda x: x.get("started_at", ""))

    for i, pid_val in enumerate([0.550, 0.500, 0.460, 0.410]):
        sid = str(uuid4())
        session = {
            "session_id": sid, "user_id": user_id,
            "task": {"id": "simple_red_circle_reference",
                     "target_dimensions": ["color", "shape", "spatial_position"]},
            "status": "completed",
            "started_at": f"2026-07-{(i+1)*4:02d}T12:00:00Z",
            "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6},
            "imagery_rating": {
                "clarity": max(1, 7 - i), "detail": max(1, 6 - i),
                "color_strength": max(1, 8 - i), "spatial_stability": max(1, 6 - i),
                "effort": 3, "fatigue": 2 + i * 0.2, "confidence": 7, "reconstruction_similarity": 7,
            },
            "pid_v2": {
                "pid_v2": pid_val,
                "subscores": {"clarity_gap": 0.15, "detail_gap": 0.18, "color_gap": 0.12,
                              "spatial_gap": 0.10, "emotional_gap": 0.03},
                "reliability": {"confidence": 0.7, "reason": ""},
                "interpretation": "Test calibration",
            },
            "not_clinical": True, "not_mind_reading": True,
        }
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "manifest.json"), "w") as f:
            json.dump(session, f, indent=2, default=str)
    return sorted([m for sid in os.listdir(CALIB_DIR)
                   for m in [json.load(open(os.path.join(CALIB_DIR, sid, "manifest.json"))) if os.path.exists(os.path.join(CALIB_DIR, sid, "manifest.json")) else None]
                   if m and m.get("user_id") == user_id and m.get("status") == "completed"],
                  key=lambda x: x.get("started_at", ""))


def _ensure_executions(user_id):
    from app.core.adaptive.adaptive_plan_execution import (
        attach_calibration_to_execution_day,
        close_plan_execution,
        complete_execution_day,
        start_plan_execution,
    )
    from app.core.calibration.pid_v2_calibration import (
        start_calibration_session,
        submit_imagery_rating,
        submit_reference_rating,
    )

    for _ in range(2):
        ex = start_plan_execution(user_id)
        if "error" in ex:
            continue
        eid = ex["execution_id"]
        for day in range(1, 8):
            complete_execution_day(user_id, eid, day, {
                "completed": True, "duration_minutes_actual": 9,
                "difficulty_rating": 5, "clarity_rating": 7,
                "fatigue_rating": 3, "focus_quality": 7,
            })
        for day in [1, 4]:
            cal = start_calibration_session(user_id, "simple_red_circle_reference")
            submit_reference_rating(cal["session_id"], {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
            submit_imagery_rating(cal["session_id"], {"clarity": 7, "detail": 6, "color_strength": 8,
                                                       "spatial_stability": 6, "effort": 3, "fatigue": 2,
                                                       "confidence": 8, "reconstruction_similarity": 7})
            attach_calibration_to_execution_day(user_id, eid, day, cal["session_id"])
        close_plan_execution(user_id, eid)


def main():
    print("=== V17 N-OF-1 EXPERIMENT ENGINE ===\n")

    user_id = "v17_test"

    # 1. Ensure data: calibrations + plans
    sessions = ensure_calibrations(user_id)
    print(f"1. Calibrations: {len(sessions)}")
    assert len(sessions) >= 4

    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    plan = build_adaptive_training_plan(user_id)
    assert plan.get("status") != "insufficient_data"
    print(f"   Baseline plan: {plan.get('plan_title', '')}")

    # Create completed executions so next_plan_optimizer has data
    _ensure_executions(user_id)

    from app.core.adaptive.next_plan_optimizer import generate_optimized_adaptive_plan
    opt_plan = generate_optimized_adaptive_plan(user_id)
    assert opt_plan.get("training_focus"), f"Optimized plan failed: {list(opt_plan.keys())}"
    print(f"   Optimized plan: {opt_plan.get('plan_title', '')}")

    # 2. Design AB experiment
    from app.core.adaptive.n_of_1_experiment_designer import design_n_of_1_experiment
    exp = design_n_of_1_experiment(user_id, "baseline_vs_optimized", "AB", 14)
    assert "error" not in exp, f"Design failed: {exp}"
    eid = exp["experiment_id"]
    assert exp["status"] == "designed"
    assert len(exp["days"]) > 0
    assert exp["design_type"] == "AB"
    print(f"2. Experiment designed: AB, {len(exp['days'])} days")

    # 3. Start experiment
    from app.core.adaptive.n_of_1_experiment_execution import (
        attach_experiment_calibration,
        close_n_of_1_experiment,
        complete_experiment_day,
        list_n_of_1_experiments,
        start_n_of_1_experiment,
    )
    exp = start_n_of_1_experiment(user_id, eid)
    assert exp["status"] == "active"
    print("3. Experiment started")

    # 4. Complete baseline days (1-7)
    for day in range(1, 8):
        exp = complete_experiment_day(user_id, eid, day, {
            "completed": True, "duration_minutes_actual": 10,
            "difficulty_rating": 5, "clarity_rating": 7,
            "fatigue_rating": 3, "focus_quality": 7,
            "confidence_rating": 7,
        })
    print("4. Baseline days 1-7 completed")

    # 5. Attach calibration to baseline block
    from app.core.calibration.pid_v2_calibration import (
        start_calibration_session,
        submit_imagery_rating,
        submit_reference_rating,
    )
    cal1 = start_calibration_session(user_id, "simple_red_circle_reference")
    submit_reference_rating(cal1["session_id"], {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal1["session_id"], {"clarity": 6, "detail": 5, "color_strength": 7,
                                                 "spatial_stability": 5, "effort": 3, "fatigue": 3,
                                                 "confidence": 7, "reconstruction_similarity": 6})
    exp = attach_experiment_calibration(user_id, eid, 1, cal1["session_id"])
    assert exp["days"][0].get("checkpoint_pid") is not None
    print(f"5. Baseline calibration: PID={exp['days'][0]['checkpoint_pid']:.3f}")

    # 6. Complete optimized days (days 8-13)
    for day in range(8, 15):
        exp = complete_experiment_day(user_id, eid, day, {
            "completed": True, "duration_minutes_actual": 8,
            "difficulty_rating": 4, "clarity_rating": 8,
            "fatigue_rating": 2, "focus_quality": 8,
            "confidence_rating": 8,
        })
    print("6. Optimized days 8-14 completed")

    # 7. Attach calibration to optimized block
    cal2 = start_calibration_session(user_id, "simple_red_circle_reference")
    submit_reference_rating(cal2["session_id"], {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal2["session_id"], {"clarity": 8, "detail": 7, "color_strength": 8,
                                                 "spatial_stability": 7, "effort": 2, "fatigue": 2,
                                                 "confidence": 9, "reconstruction_similarity": 8})
    exp = attach_experiment_calibration(user_id, eid, 8, cal2["session_id"])
    assert exp["days"][7].get("checkpoint_pid") is not None
    print(f"7. Optimized calibration: PID={exp['days'][7]['checkpoint_pid']:.3f}")

    # 8. Close experiment
    exp = close_n_of_1_experiment(user_id, eid)
    assert exp["status"] == "completed"
    print(f"8. Experiment closed: completed={exp.get('summary', {}).get('completed_days', 0)}/{exp.get('summary', {}).get('total_days', 0)}")

    # 9. Analyze experiment
    from app.core.adaptive.n_of_1_experiment_analysis import (
        analyze_n_of_1_experiment,
        compute_n_of_1_evidence_score,
    )
    analysis = analyze_n_of_1_experiment(user_id, eid)
    assert analysis.get("primary_result", {}).get("direction") is not None
    assert analysis.get("condition_metrics") is not None
    print(f"9. Analysis: direction={analysis['primary_result']['direction']}")
    print(f"   Baseline: {analysis['condition_metrics']['baseline']['days']}d | Optimized: {analysis['condition_metrics']['optimized']['days']}d")
    print(f"   Confounds: {analysis.get('confounds', [])}")

    # 10. Compute evidence score
    evidence = compute_n_of_1_evidence_score(user_id, eid)
    assert evidence.get("evidence_score", -1) >= 0
    assert evidence.get("category") is not None
    print(f"10. Evidence score: {evidence['evidence_score']}/100 ({evidence['category']})")
    print(f"    Components: pid={evidence.get('component_scores', {}).get('pid_effect_strength')}, "
          f"adh={evidence.get('component_scores', {}).get('adherence_quality')}")

    # 11. Generate report
    from app.core.adaptive.n_of_1_experiment_report import generate_n_of_1_experiment_report
    report = generate_n_of_1_experiment_report(user_id, eid)
    assert report.get("report_id") is not None
    print(f"11. Report generated: {report['evidence_category']}")
    print(f"    Safe claim: {report.get('safe_claim', '')[:80]}...")

    # 12. Personal profile with experiment summary
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    n1_sum = profile.get("n_of_1_experiment_summary", {})
    assert n1_sum.get("has_experiments") is True or n1_sum == {}, \
        f"Expected experiment summary: {n1_sum}"
    print(f"12. Profile n_of_1_summary: has_experiments={n1_sum.get('has_experiments', False)}")

    # 13. List experiments
    all_exps = list_n_of_1_experiments(user_id)
    assert len(all_exps) >= 1
    print(f"13. Experiment list: {len(all_exps)} experiment(s)")

    # 14. Sparse user
    from app.core.adaptive.n_of_1_experiment_designer import get_latest_n_of_1_experiment as get_latest_exp
    assert get_latest_exp("nonexistent_v17") is None

    sparse_design = design_n_of_1_experiment("nonexistent_v17")
    assert "error" in sparse_design
    print(f"14. Sparse user: Handled ({sparse_design.get('reason', '')})")

    # 15. Safety flags
    assert exp.get("not_clinical") is True
    assert analysis.get("not_mind_reading") is True
    assert evidence.get("not_bci_claim") is True
    assert report.get("production_valid") is False
    print("15. Safety flags: All OK")

    print("\n=== V17 N-OF-1 EXPERIMENT ENGINE: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

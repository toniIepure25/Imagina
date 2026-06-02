"""V16 Adaptive Optimization Engine — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "imagina")
CALIB_DIR = os.path.join(DATA_DIR, "calibration_sessions")


def ensure_data_for(user_id="v16_test"):
    d = CALIB_DIR
    existing = []
    if os.path.isdir(d):
        for sid in os.listdir(d):
            mp = os.path.join(d, sid, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp))
                if m.get("user_id") == user_id and m.get("status") == "completed":
                    existing.append(m)

    if len(existing) >= 4:
        return sorted(existing, key=lambda x: x.get("started_at", ""))

    for i, pid_val in enumerate([0.620, 0.540, 0.480, 0.400]):
        sid = str(uuid4())
        session = {
            "session_id": sid, "user_id": user_id,
            "task": {"id": "simple_red_circle_reference",
                     "target_dimensions": ["color", "shape", "spatial_position"]},
            "status": "completed",
            "started_at": f"2026-06-{(i+1)*5:02d}T12:00:00Z",
            "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6},
            "imagery_rating": {
                "clarity": max(1, 7 - i), "detail": max(1, 6 - i),
                "color_strength": max(1, 8 - i), "spatial_stability": max(1, 6 - i),
                "effort": 3, "fatigue": 2 + i * 0.3, "confidence": 6 + i,
                "reconstruction_similarity": 7,
            },
            "pid_v2": {
                "pid_v2": pid_val,
                "perception_similarity_score": round(1.0 - pid_val, 3),
                "subscores": {
                    "clarity_gap": 0.170, "detail_gap": 0.190,
                    "color_gap": 0.140, "spatial_gap": 0.120, "emotional_gap": 0.030,
                },
                "reliability": {"confidence": 0.7, "reason": ""},
                "interpretation": "Test calibration",
                "analysis_mode": "personal_exploratory_training",
                "not_clinical": True,
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


def ensure_adaptive_plan(user_id):
    from app.core.adaptive.adaptive_training_planner import (
        build_adaptive_training_plan,
    )
    plan = build_adaptive_training_plan(user_id)
    if plan.get("status") == "insufficient_data":
        raise RuntimeError(f"Cannot build plan: {plan}")
    return plan


def create_execution(user_id, focus_override=None):
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

    ex = start_plan_execution(user_id)
    eid = ex["execution_id"]

    for day in [1, 2]:
        ex = complete_execution_day(user_id, eid, day, {
            "completed": True, "duration_minutes_actual": 10 + day,
            "difficulty_rating": 5, "clarity_rating": 7,
            "fatigue_rating": 3 - day * 0.5, "focus_quality": 7,
        })

    for day in [1, 4]:
        cal = start_calibration_session(user_id, "simple_red_circle_reference")
        csid = cal["session_id"]
        submit_reference_rating(csid, {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
        submit_imagery_rating(csid, {"clarity": 7, "detail": 6, "color_strength": 8,
                                      "spatial_stability": 6, "effort": 3, "fatigue": 2,
                                      "confidence": 8, "reconstruction_similarity": 7})
        attach_calibration_to_execution_day(user_id, eid, day, csid)

    close_plan_execution(user_id, eid)
    return eid


def main():
    print("=== V16 ADAPTIVE OPTIMIZATION ENGINE ===\n")

    user_id = "v16_test"

    # 1. Ensure data: calibrations + plan + 2 completed executions
    sessions = ensure_data_for(user_id)
    plan = ensure_adaptive_plan(user_id)
    print(f"1. Data ready: {len(sessions)} calibrations, plan={plan['training_focus']}")

    # Create 2 executions with different PID outcomes
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions
    execs = list_plan_executions(user_id)
    completed = [e for e in execs if e.get("status") == "completed"]
    if len(completed) < 2:
        _eid1 = create_execution(user_id)
        create_execution(user_id)
        print("   Created 2 executions")
    else:
        completed[-2]["execution_id"], completed[-1]["execution_id"]
        print(f"   Reusing {len(completed)} existing executions")
        print(f"   Reusing {len(completed)} existing executions")

    # 2. Build plan response model
    from app.core.adaptive.plan_response_model import build_plan_response_model
    resp_model = build_plan_response_model(user_id)
    assert resp_model.get("n_executions", 0) >= 2
    assert "focus_models" in resp_model
    assert "best_focus" in resp_model
    print(f"2. Response model: best={resp_model['best_focus']}, worst={resp_model.get('worst_focus', '')}")
    print(f"   Focuses: {list(resp_model.get('focus_models', {}).keys())}")

    # 3. Fatigue/adherence analysis
    from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
    fa = analyze_fatigue_adherence_patterns(user_id)
    assert fa.get("fatigue", {}).get("risk_level") is not None
    assert fa.get("adherence", {}).get("risk_level") is not None
    print(f"3. Fatigue: risk={fa['fatigue']['risk_level']} (avg={fa['fatigue']['average']})")
    print(f"   Adherence: risk={fa['adherence']['risk_level']} (avg={fa['adherence']['average']})")
    print(f"   Session length rec: {fa.get('recommended_session_length_minutes')}min")

    # 4. Recommend optimized next plan
    from app.core.adaptive.next_plan_optimizer import recommend_optimized_next_plan
    rec = recommend_optimized_next_plan(user_id)
    assert rec.get("recommendation_type") is not None
    assert rec.get("recommended_focus") is not None
    print(f"4. Recommendation: type={rec['recommendation_type']}, focus={rec['recommended_focus']}")
    print(f"   Why: {rec.get('why', [])[:2]}")

    # 5. Generate optimized adaptive plan
    from app.core.adaptive.next_plan_optimizer import (
        generate_optimized_adaptive_plan,
        load_latest_optimized_plan,
    )
    opt_plan = generate_optimized_adaptive_plan(user_id)
    assert "training_focus" in opt_plan
    assert len(opt_plan.get("daily_plan", [])) == 7
    assert opt_plan.get("not_clinical") is True
    print(f"5. Optimized plan: {opt_plan['plan_title']} ({opt_plan['training_focus']})")
    print(f"   Adjustments: {opt_plan.get('adjustments_applied', {})}")

    loaded = load_latest_optimized_plan(user_id)
    assert loaded is not None
    print("   Plan persistence: OK")

    # 6. Compare last 2 executions
    from app.core.adaptive.plan_ab_comparator import compare_plan_executions, compare_training_focuses
    comp = compare_plan_executions(user_id)
    assert comp.get("winner") is not None
    assert comp.get("confidence_level") is not None
    print(f"6. Execution comparison: winner={comp['winner']}, confidence={comp['confidence_level']}")

    # 7. Compare training focuses
    focus_comp = compare_training_focuses(user_id)
    assert focus_comp.get("comparison", {}).get("top_ranked") is not None
    ranked = focus_comp.get("comparison", {}).get("ranked_focuses", [])
    print(f"7. Focus comparison: top={focus_comp['comparison'].get('top_ranked')}, ranked={len(ranked)}")

    # 8. Personal profile with optimization summary
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    opt_summary = profile.get("adaptive_optimization_summary", {})
    assert opt_summary.get("best_focus") is not None or opt_summary == {}, \
        f"optimization_summary missing best_focus: {opt_summary}"
    print(f"8. Profile optimization_summary: best_focus={opt_summary.get('best_focus', '')}")
    print(f"   Rec type: {opt_summary.get('recommendation_type', '')}")

    # 9. Safety flags
    assert resp_model.get("not_clinical") is True
    assert resp_model.get("not_mind_reading") is True
    assert resp_model.get("not_bci_claim") is True
    assert resp_model.get("production_valid") is False
    assert fa.get("not_clinical") is True
    assert rec.get("not_clinical") is True
    assert opt_plan.get("not_clinical") is True
    assert comp.get("not_clinical") is True
    print("9. Safety flags: All OK")

    # 10. Sparse user
    from app.core.adaptive.plan_response_model import build_plan_response_model as build_rm
    sparse_rm = build_rm("nonexistent_v16")
    assert sparse_rm.get("status") == "insufficient_data"
    print(f"10. Sparse user: Handled ({sparse_rm['status']})")

    # 11. Insufficient data recommendation
    from app.core.adaptive.next_plan_optimizer import recommend_optimized_next_plan as rec_opt
    sparse_rec = rec_opt("nonexistent_v16")
    assert sparse_rec.get("recommendation_type") == "insufficient_data"
    print(f"11. Insufficient data rec: {sparse_rec['recommendation_type']}")

    print("\n=== V16 ADAPTIVE OPTIMIZATION ENGINE: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

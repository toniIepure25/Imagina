"""V14 Adaptive PID Training Loop — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "imagina", "calibration_sessions")


def ensure_calibration_sessions(user_id="v14_test"):
    d = DATA_DIR
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

    # Create synthetic improving sessions
    sessions = []
    pid_values = [0.650, 0.520, 0.480, 0.350]
    for i, pid_val in enumerate(pid_values):
        sid = str(uuid4())
        session = {
            "session_id": sid,
            "user_id": user_id,
            "task": {"id": "simple_red_circle_reference",
                     "target_dimensions": ["color", "shape", "spatial_position"]},
            "status": "completed",
            "started_at": f"2026-05-{(i+1)*6:02d}T12:00:00Z",
            "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6},
            "imagery_rating": {
                "clarity": max(1, 6 - i), "detail": max(1, 5 - i),
                "color_strength": max(1, 7 - i), "spatial_stability": max(1, 5 - i),
                "effort": 4, "fatigue": 3, "confidence": 7, "reconstruction_similarity": 7 - i * 0.5,
            },
            "pid_v2": {
                "pid_v2": pid_val,
                "perception_similarity_score": round(1.0 - pid_val, 3),
                "subscores": {
                    "clarity_gap": 0.200 - i * 0.03, "detail_gap": 0.250 - i * 0.04,
                    "color_gap": 0.180 - i * 0.02, "spatial_gap": 0.150 - i * 0.03,
                    "emotional_gap": 0.050,
                },
                "reliability": {"confidence": 0.7, "reason": ""},
                "interpretation": "Test calibration",
                "analysis_mode": "personal_exploratory_training",
                "not_clinical": True,
            },
        }
        sd = os.path.join(DATA_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "manifest.json"), "w") as f:
            json.dump(session, f, indent=2, default=str)
        sessions.append(session)
    return sessions


def main():
    print("=== V14 ADAPTIVE PID TRAINING LOOP ===\n")

    user_id = "v14_test"

    # 1. Ensure calibration sessions
    sessions = ensure_calibration_sessions(user_id)
    print(f"1. Calibration sessions: {len(sessions)}")
    assert len(sessions) >= 2
    print(f"   PIDs: {[s['pid_v2']['pid_v2'] for s in sessions]}")

    # 2. Build adaptive training plan
    from app.core.adaptive.adaptive_training_planner import (
        build_adaptive_training_plan,
        generate_daily_plan_from_focus,
        list_adaptive_training_plans,
        load_latest_adaptive_training_plan,
    )

    plan = build_adaptive_training_plan(user_id)
    assert plan.get("status") != "insufficient_data", f"Plan build failed: {plan}"
    print(f"2. Plan built: {plan['training_focus']}")
    print(f"   Title: {plan['plan_title']}")
    print(f"   Weakest: {plan['source']['weakest_dimension']}")
    print(f"   Mean PID: {plan['source']['mean_pid_v2']}")
    print(f"   Daily plan: {len(plan['daily_plan'])} days")
    print(f"   Checkpoints: {len(plan['checkpoint_schedule'])}")

    # 3. Save/load
    loaded = load_latest_adaptive_training_plan(user_id)
    assert loaded is not None
    assert loaded["training_focus"] == plan["training_focus"]
    print("3. Plan load/verify: OK")

    # 4. List plans
    plans = list_adaptive_training_plans(user_id)
    assert len(plans) >= 1
    print(f"4. Plan history: {len(plans)} snapshot(s)")

    # 5. PID improvement tracker
    from app.core.adaptive.pid_improvement_tracker import (
        compute_pid_improvement,
        compute_training_response,
    )

    imp = compute_pid_improvement(user_id)
    assert imp.get("n_sessions", 0) >= 2
    assert "trend" in imp
    assert "meaningful_change" in imp
    assert "dimension_changes" in imp
    assert imp.get("not_clinical") is True
    print(f"5. PID improvement: {imp['first_pid']:.3f} → {imp['latest_pid']:.3f}, trend={imp['trend']}")
    print(f"   Meaningful: {imp['meaningful_change']}")
    print(f"   Dim changes: {sorted(imp['dimension_changes'].keys())}")

    # 6. Training response
    tr = compute_training_response(user_id)
    assert "training_response" in tr
    assert tr.get("has_active_plan") is True
    print(f"6. Training response: {tr['training_response']}")

    # 7. Rebuild personal profile
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    adaptive = profile.get("adaptive_training_summary", {})
    assert adaptive.get("has_active_plan") is True, f"Expected active plan in summary: {adaptive}"
    print("7. Profile rebuilt: adaptive_summary present")
    print(f"   Plan: {adaptive.get('current_plan_title', '')}")
    print(f"   Trend: {adaptive.get('pid_trend', '')}")

    # 8. Safety flags
    assert plan.get("not_clinical") is True
    assert plan.get("not_mind_reading") is True
    assert plan.get("not_bci_claim") is True
    assert plan.get("production_valid") is False
    assert imp.get("not_clinical") is True
    assert tr.get("not_clinical") is True
    print("8. Safety flags: All OK")

    # 9. Sparse user
    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan as build_plan
    sparse = build_plan("nonexistent_v14")
    assert sparse.get("status") == "insufficient_data"
    print(f"9. Sparse user: Handled ({sparse['status']})")

    # 10. Exercise generation
    exercises = generate_daily_plan_from_focus("vividness_foundation", "clarity_gap", "simple_red_circle_reference")
    assert len(exercises) == 7
    assert "title" in exercises[0]
    assert "day" in exercises[0]
    print("10. Exercises: 7 days generated for vividness_foundation")

    # 11. Different foci
    for focus in ["detail_generation", "spatial_stability_training", "color_intensity_training"]:
        ex = generate_daily_plan_from_focus(focus, f"{focus}_gap", "dummy_task")
        assert len(ex) == 7, f"{focus} has {len(ex)} days"
    print("11. All foci generate valid plans")

    # 12. Empty plan regeneration
    from app.core.adaptive.adaptive_training_planner import save_adaptive_training_plan
    save_adaptive_training_plan(user_id, plan)
    reloaded = load_latest_adaptive_training_plan(user_id)
    assert reloaded["plan_title"] == plan["plan_title"]
    print("12. Regenerate persistence: OK")

    print("\n=== V14 ADAPTIVE PID TRAINING LOOP: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

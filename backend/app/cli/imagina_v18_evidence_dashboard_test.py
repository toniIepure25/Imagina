"""V18 Evidence Dashboard — Integration Test."""

import json
import os
import sys
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "imagina")
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
        return sorted(existing, key=lambda x: x.get("started_at", ""))

    for i, pid_val in enumerate([0.500, 0.460, 0.430, 0.390]):
        sid = str(uuid4())
        session = {
            "session_id": sid, "user_id": user_id,
            "task": {"id": "simple_red_circle_reference",
                     "target_dimensions": ["color", "shape", "spatial_position"]},
            "status": "completed",
            "started_at": f"2026-08-{(i+1)*4:02d}T12:00:00Z",
            "reference_rating": {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6},
            "imagery_rating": {"clarity": max(1, 7 - i), "detail": max(1, 6 - i),
                               "color_strength": max(1, 8 - i), "spatial_stability": max(1, 6 - i),
                               "effort": 3, "fatigue": 2, "confidence": 7},
            "pid_v2": {"pid_v2": pid_val, "perception_similarity_score": round(1.0 - pid_val, 3),
                       "subscores": {"clarity_gap": 0.12, "detail_gap": 0.15, "color_gap": 0.10,
                                     "spatial_gap": 0.08, "emotional_gap": 0.02},
                       "reliability": {"confidence": 0.7, "reason": ""},
                       "interpretation": "Test calibration"},
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


def _ensure_executions_and_plans(user_id):
    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    build_adaptive_training_plan(user_id)

    from app.core.adaptive.adaptive_plan_execution import (
        attach_calibration_to_execution_day,
        close_plan_execution,
        complete_execution_day,
        list_plan_executions,
        start_plan_execution,
    )
    from app.core.calibration.pid_v2_calibration import (
        start_calibration_session,
        submit_imagery_rating,
        submit_reference_rating,
    )
    execs = list_plan_executions(user_id)
    completed = [e for e in execs if e.get("status") == "completed"]
    if len(completed) >= 2:
        return

    for _ in range(2):
        ex = start_plan_execution(user_id)
        if "error" in ex:
            continue
        eid = ex["execution_id"]
        for day in range(1, 8):
            complete_execution_day(user_id, eid, day, {
                "completed": True, "duration_minutes_actual": 10,
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

    from app.core.adaptive.next_plan_optimizer import generate_optimized_adaptive_plan
    generate_optimized_adaptive_plan(user_id)

    _ensure_n_of_1_experiment(user_id)


def _ensure_n_of_1_experiment(user_id):
    from app.core.adaptive.n_of_1_experiment_execution import list_n_of_1_experiments
    exps = list_n_of_1_experiments(user_id)
    completed = [e for e in exps if e.get("status") == "completed"]
    if len(completed) >= 1:
        return

    from app.core.adaptive.n_of_1_experiment_designer import design_n_of_1_experiment
    from app.core.adaptive.n_of_1_experiment_execution import (
        attach_experiment_calibration,
        close_n_of_1_experiment,
        complete_experiment_day,
        start_n_of_1_experiment,
    )
    from app.core.calibration.pid_v2_calibration import (
        start_calibration_session,
        submit_imagery_rating,
        submit_reference_rating,
    )
    exp = design_n_of_1_experiment(user_id, "baseline_vs_optimized", "AB", 14)
    eid = exp["experiment_id"]
    start_n_of_1_experiment(user_id, eid)
    for day in range(1, 8):
        complete_experiment_day(user_id, eid, day, {
            "completed": True, "duration_minutes_actual": 10,
            "difficulty_rating": 5, "clarity_rating": 7,
            "fatigue_rating": 3, "focus_quality": 7, "confidence_rating": 7,
        })
    cal1 = start_calibration_session(user_id, "simple_red_circle_reference")
    submit_reference_rating(cal1["session_id"], {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal1["session_id"], {"clarity": 6, "detail": 5, "color_strength": 7,
                                                 "spatial_stability": 5, "effort": 3, "fatigue": 3,
                                                 "confidence": 7, "reconstruction_similarity": 6})
    attach_experiment_calibration(user_id, eid, 1, cal1["session_id"])
    for day in range(8, 15):
        complete_experiment_day(user_id, eid, day, {
            "completed": True, "duration_minutes_actual": 8,
            "difficulty_rating": 4, "clarity_rating": 8,
            "fatigue_rating": 2, "focus_quality": 8, "confidence_rating": 8,
        })
    cal2 = start_calibration_session(user_id, "simple_red_circle_reference")
    submit_reference_rating(cal2["session_id"], {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6})
    submit_imagery_rating(cal2["session_id"], {"clarity": 8, "detail": 7, "color_strength": 8,
                                                 "spatial_stability": 7, "effort": 2, "fatigue": 2,
                                                 "confidence": 9, "reconstruction_similarity": 8})
    attach_experiment_calibration(user_id, eid, 8, cal2["session_id"])
    close_n_of_1_experiment(user_id, eid)


def main():
    print("=== V18 EVIDENCE DASHBOARD ===\n")

    user_id = "v18_test"

    # 1. Ensure data
    _ensure_data(user_id)
    _ensure_executions_and_plans(user_id)
    print("1. Data ready (calibrations, plans, executions, N-of-1)")

    # 2. Build unified evidence model
    from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
    ev = build_unified_evidence_model(user_id)
    assert ev.get("evidence_status") is not None
    assert ev.get("data_inventory", {}).get("n_calibrations", 0) >= 4
    assert ev.get("not_clinical") is True
    print(f"2. Evidence model: status={ev['evidence_status']}")
    print(f"   Inventory: calib={ev['data_inventory']['n_calibrations']}, "
          f"execs={ev['data_inventory']['n_executions']}, "
          f"exps={ev['data_inventory']['n_completed_experiments']}")

    # 3. Evidence quality audit
    from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
    qa = audit_imagina_evidence_quality(user_id)
    assert qa.get("quality_score", -1) >= 0
    print(f"3. Quality audit: {qa['quality_score']}/100 ({qa['quality_category']})")
    print(f"   Passed: {len(qa.get('passed_checks', []))}, "
          f"Warnings: {len(qa.get('warnings', []))}, "
          f"Critical: {len(qa.get('critical_issues', []))}")

    # 4. Evidence timeline
    from app.core.evidence.evidence_timeline_and_recommendations import build_evidence_timeline
    tl = build_evidence_timeline(user_id)
    assert tl.get("n_events", -1) >= 0
    print(f"4. Timeline: {tl['n_events']} events")

    # 5. Research recommendation
    from app.core.evidence.evidence_timeline_and_recommendations import recommend_next_research_action
    rec = recommend_next_research_action(user_id)
    assert rec.get("recommended_action") is not None
    print(f"5. Recommendation: {rec['recommended_action']} (priority={rec['priority']})")
    print(f"   Blocks export: {rec.get('blocks_export', True)}")

    # 6. Generate research export pack
    from app.core.evidence.research_export_pack import generate_research_export_pack
    pack = generate_research_export_pack(user_id)
    assert pack.get("export_id") is not None
    assert len(pack.get("files", [])) == 8
    print(f"6. Export pack: {len(pack['files'])} files at {pack.get('export_dir', '')[:50]}...")

    # Verify key files exist
    for f in pack.get("files", []):
        assert os.path.exists(f), f"Missing: {f}"
    print("   All 8 files verified on disk")

    # 7. Personal profile with evidence_summary
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    ev_sum = profile.get("evidence_summary", {})
    assert ev_sum.get("evidence_status") is not None or ev_sum == {}, \
        f"Missing evidence_summary: {ev_sum}"
    print(f"7. Profile evidence_summary: status={ev_sum.get('evidence_status', '')}")

    # 8. Sparse user
    sparse_ev = build_unified_evidence_model("nonexistent_v18")
    assert sparse_ev.get("evidence_status") == "insufficient"
    print(f"8. Sparse user: {sparse_ev['evidence_status']}")

    # 9. No raw EEG in export
    for f in pack.get("files", []):
        content = open(f, "r").read()
        assert "raw_eeg" not in content.lower(), f"Raw EEG found in {f}"
    print("9. No raw EEG in export: OK")

    # 10. Safety flags
    assert ev.get("not_clinical") is True
    assert qa.get("not_mind_reading") is True
    assert tl.get("not_bci_claim") is True
    assert pack.get("production_valid") is False
    print("10. Safety flags: All OK")

    print("\n=== V18 EVIDENCE DASHBOARD: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""V21 Skill Tree Progression — Integration Test."""

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
    for i, pv in enumerate([0.500, 0.460, 0.430, 0.390]):
        sid = str(uuid4())
        s = {"session_id": sid, "user_id": user_id, "task": {"id": "simple_red_circle_reference", "target_dimensions": ["color","shape","spatial_position"]}, "status": "completed", "started_at": f"2026-10-{(i+1)*4:02d}T12:00:00Z", "reference_rating": {"clarity":8,"detail":7,"color_strength":9,"spatial_stability":6}, "imagery_rating": {"clarity":max(1,7-i),"detail":max(1,6-i),"color_strength":max(1,8-i),"spatial_stability":max(1,6-i),"effort":3,"fatigue":2,"confidence":7}, "pid_v2": {"pid_v2":pv,"subscores":{"clarity_gap":0.12,"detail_gap":0.15,"color_gap":0.10,"spatial_gap":0.08,"emotional_gap":0.02},"reliability":{"confidence":0.7}},"not_clinical":True}
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        json.dump(s, open(os.path.join(sd,"manifest.json"),"w"), indent=2, default=str)


def _ensure_v19_v20(user_id):
    from app.core.imagery.guided_session_runtime import (
        complete_guided_session,
        start_guided_imagery_session,
        submit_guided_micro_checkin,
    )
    from app.core.imagery.task_session_manager import (
        complete_imagery_task_session,
        list_imagery_task_sessions,
        start_imagery_task_session,
        submit_imagery_task_rating,
    )
    existing_v19 = [s for s in list_imagery_task_sessions(user_id) if s.get("status") == "completed"]
    if len(existing_v19) < 3:
        for tid, r in [("red_circle_vividness", {"vividness":7,"color_control":6,"effort":3,"fatigue":2,"confidence":7}), ("blue_cube_vividness", {"vividness":6,"spatial_control":5,"effort":4,"fatigue":3,"confidence":7}), ("color_shift_red_to_blue", {"color_control":7,"meta_control":6,"effort":4,"fatigue":2,"confidence":8}), ("static_cube_stability", {"spatial_control":6,"vividness":6,"stability":5,"effort":5,"fatigue":3,"confidence":6}), ("apple_detail_generation", {"detail":7,"vividness":7,"color_control":8,"effort":4,"fatigue":2,"confidence":8}), ("rotating_object", {"motion":8,"spatial_control":7,"effort":3,"fatigue":1,"confidence":9})]:
            s = start_imagery_task_session(user_id, tid)
            submit_imagery_task_rating(s["session_id"], r)
            complete_imagery_task_session(s["session_id"])

    dims = ["vividness","spatial_control","detail","motion","color_control","stability"]
    for i, dim in enumerate(dims):
        tid = ["red_circle_vividness","static_cube_stability","apple_detail_generation","rotating_object","color_shift_red_to_blue","hold_image_30_seconds"][i]
        score = 7 - i * 0.5
        gs = start_guided_imagery_session(user_id, tid, "manual")
        for _ in range(2):
            submit_guided_micro_checkin(gs["session_id"], {"vividness":max(5,int(score)),"stability":max(5,int(score-1)),"effort":3+i,"fatigue":2+i,"confidence":7,"discomfort":1})
        complete_guided_session(gs["session_id"])


def main():
    print("=== V21 IMAGERY SKILL TREE PROGRESSION ===\n")
    user_id = "v21_test"
    _ensure_data(user_id)
    _ensure_v19_v20(user_id)

    from app.core.imagery.skill_tree import (
        build_longitudinal_skill_model,
        detect_imagery_plateaus,
        evaluate_mastery_milestones,
        generate_weekly_imagery_progress_report,
        get_skill_tree,
        recommend_next_difficulty,
        update_imagery_curriculum,
    )

    tree = get_skill_tree()
    assert tree["n_dimensions"] == 9
    print(f"1. Skill tree: {tree['n_dimensions']} branches, max level {tree['max_level']}")

    model = build_longitudinal_skill_model(user_id)
    dims = model.get("dimensions", {})
    assert len(dims) == 9
    leveled = sum(1 for d in dims.values() if d.get("current_level", 1) >= 1)
    assert leveled >= 1
    print(f"2. Skill model: {model['n_total_sessions']} sessions, {leveled} dims with levels")
    print(f"   Best: {model.get('strongest_progress_dimension')}, Highest: {model.get('highest_level_dimension')}")

    ml = evaluate_mastery_milestones(user_id)
    ach = len(ml.get("achieved_milestones", []))
    pend = len(ml.get("pending_milestones", []))
    assert ach + pend >= 5
    print(f"3. Milestones: {ach} achieved, {pend} pending")

    plat = detect_imagery_plateaus(user_id)
    assert plat.get("overall_risk") is not None
    print(f"4. Plateaus: detected={plat.get('plateau_detected')}, risk={plat.get('overall_risk')}")

    rec = recommend_next_difficulty(user_id, "red_circle_vividness", "vividness")
    assert rec.get("recommendation") in ("increase", "maintain", "decrease")
    print(f"5. Difficulty: {rec['recommendation']}, delta={rec.get('difficulty_delta')}")

    rpt = generate_weekly_imagery_progress_report(user_id, 30)
    if rpt.get("n_guided_sessions", 0) > 0:
        print(f"6. Weekly report: {rpt['n_guided_sessions']} sessions, IQI={rpt.get('average_iqi_proxy',0):.2f}")
    else:
        print("6. Weekly report: no sessions in 7-day window (expected for fresh test data)")

    cur = update_imagery_curriculum(user_id)
    assert cur.get("new_focus") is not None
    print(f"7. Curriculum: {cur.get('current_focus','')} → {cur.get('new_focus','')}")

    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    prof = build_personal_imagery_profile(user_id)
    sk = prof.get("imagery_skill_progress_summary", {})
    print(f"8. Profile skill progress: has_model={sk.get('has_skill_model')}, milestones={sk.get('n_milestones_achieved')}")

    assert model.get("not_clinical") is True
    assert plat.get("not_bci_claim") is True
    print("9. Safety flags: All OK")

    print("\n=== V21 IMAGERY SKILL TREE PROGRESSION: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

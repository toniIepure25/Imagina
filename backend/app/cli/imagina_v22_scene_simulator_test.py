"""V22 Scene Simulator — Integration Test."""

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
        s = {"session_id": sid, "user_id": user_id, "task": {"id": "simple_red_circle_reference", "target_dimensions": ["color","shape","spatial_position"]}, "status": "completed", "started_at": f"2026-11-{(i+1)*4:02d}T12:00:00Z", "reference_rating": {"clarity":8,"detail":7,"color_strength":9,"spatial_stability":6}, "imagery_rating": {"clarity":max(1,7-i),"detail":max(1,6-i),"color_strength":max(1,8-i),"spatial_stability":max(1,6-i),"effort":3,"fatigue":2,"confidence":7}, "pid_v2": {"pid_v2":pv,"subscores":{"clarity_gap":0.12,"detail_gap":0.15,"color_gap":0.10,"spatial_gap":0.08,"emotional_gap":0.02},"reliability":{"confidence":0.7}},"not_clinical":True}
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        json.dump(s, open(os.path.join(sd,"manifest.json"),"w"), indent=2, default=str)


def main():
    print("=== V22 MENTAL SCENE SIMULATOR ===\n")
    user_id = "v22_test"
    _ensure_data(user_id)

    from app.core.imagery.scene_simulator import (
        build_guided_session_replay,
        export_guided_session_replay_summary,
        get_guided_session_replay,
        get_latest_scene_state,
        get_scene_control_summary,
        get_scene_template,
        get_scene_template_for_task,
        get_scene_template_registry,
        list_scene_states,
        update_scene_from_guided_session,
    )

    reg = get_scene_template_registry()
    assert reg["n_templates"] >= 10, f"Only {reg['n_templates']} templates"
    print(f"1. Registry: {reg['n_templates']} templates")

    tpl = get_scene_template("red_circle_field")
    assert "error" not in tpl
    assert tpl["title"] == "Red Circle Field"
    print(f"2. Template: {tpl['title']}")

    mapped = get_scene_template_for_task("apple_detail_generation")
    assert mapped["template_id"] == "apple_detail_table"
    print(f"3. Task mapping: apple → {mapped['template_id']}")

    from app.core.imagery.guided_session_runtime import (
        advance_guided_session_phase,
        complete_guided_session,
        start_guided_imagery_session,
        submit_guided_micro_checkin,
    )
    gs = start_guided_imagery_session(user_id, "red_circle_vividness", "manual")
    sid = gs["session_id"]
    print(f"4. Session started: {sid[:12]}...")

    r1 = submit_guided_micro_checkin(sid, {"vividness": 5, "stability": 4, "effort": 5, "fatigue": 4, "confidence": 6, "discomfort": 1})
    scene = r1.get("scene_state", {})
    assert scene.get("template_id") is not None, "No scene state in response"
    print(f"5. Check-in includes scene_state: template={scene.get('template_id')}")

    latest = get_latest_scene_state(sid)
    assert latest and "error" not in latest
    print(f"   Scene persisted: clarity={latest['scene_parameters']['clarity']:.2f}")

    advance_guided_session_phase(sid)
    advance_guided_session_phase(sid)
    update_scene_from_guided_session(sid)
    states = list_scene_states(sid)
    assert len(states) >= 1
    print(f"6. Advance + update: {len(states)} states so far")

    r2 = submit_guided_micro_checkin(sid, {"vividness": 8, "stability": 7, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
    s2 = r2.get("scene_state", {})
    c2 = s2.get("scene_parameters", {})
    c1 = scene.get("scene_parameters", {})
    assert c2.get("clarity", 0) > c1.get("clarity", 0), "Clarity should increase with better check-in"
    print(f"7. Clarity improved: {c1.get('clarity',0):.2f} → {c2.get('clarity',0):.2f}")

    r3 = submit_guided_micro_checkin(sid, {"vividness": 3, "stability": 2, "effort": 7, "fatigue": 7, "confidence": 4, "discomfort": 1})
    s3 = r3.get("scene_state", {})
    c3 = s3.get("scene_parameters", {})
    assert c3.get("fog", 0) > c2.get("fog", 0), "Fog should increase with low vividness/high fatigue"
    print(f"8. Fog increased: {c2.get('fog',0):.2f} → {c3.get('fog',0):.2f}")

    complete_guided_session(sid)
    final = get_latest_scene_state(sid)
    assert final and "error" not in final
    print(f"9. Session completed, final scene: clarity={final['scene_parameters']['clarity']:.2f}")

    summary = get_scene_control_summary(sid)
    assert summary["n_scene_states"] >= 1
    print(f"10. Scene summary: {summary['n_scene_states']} states, trend={summary.get('scene_trend',{})}")

    replay = build_guided_session_replay(sid)
    assert replay["n_frames"] >= 3
    assert replay.get("summary", {}).get("clarity_change") is not None
    print(f"11. Replay: {replay['n_frames']} frames, clarity_chg={replay['summary']['clarity_change']:.3f}")

    loaded_replay = get_guided_session_replay(sid)
    assert loaded_replay is not None
    print("    Replay persistence: OK")

    rep_sum = export_guided_session_replay_summary(sid)
    assert rep_sum.get("clarity_change") is not None
    print("12. Replay summary export: OK")

    bad_tpl = get_scene_template("nonexistent")
    assert "error" in bad_tpl
    print("13. Invalid template handled: OK")

    fallback = get_scene_template_for_task("nonexistent_task")
    assert fallback["template_id"] == "default_dark_field"
    print("14. Unknown task fallback: default_dark_field")

    assert tpl.get("not_clinical") is True
    assert final.get("not_mind_reading") is True
    assert replay.get("not_bci_claim") is True
    print("15. Safety flags: All OK")

    print("\n=== V22 MENTAL SCENE SIMULATOR: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

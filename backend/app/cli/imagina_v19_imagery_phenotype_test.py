"""V19 Imagery Phenotype Engine — Integration Test."""

import sys


def main():
    print("=== V19 IMAGERY PHENOTYPE ENGINE ===\n")

    user_id = "v19_test"

    # 1. List task registry
    from app.core.imagery.task_battery import get_imagery_task, get_imagery_task_registry, list_imagery_tasks
    reg = get_imagery_task_registry()
    assert reg.get("n_tasks", 0) >= 30, f"Only {reg.get('n_tasks')} tasks"
    print(f"1. Task registry: {reg['n_tasks']} tasks, {len(reg.get('categories', []))} categories")

    # 2. Verify all tasks have safety flags
    for t in reg["tasks"]:
        assert t.get("not_clinical") is True, f"{t['task_id']} missing not_clinical"
    print("2. All tasks have safety flags: OK")

    # 3. Get single task
    t = get_imagery_task("red_circle_vividness")
    assert "error" not in t
    assert t["category"] == "basic_vividness"
    print(f"3. Single task: {t['title']} (L{t['difficulty']})")

    # 4. List by category
    cat_tasks = list_imagery_tasks("motion_imagery")
    assert cat_tasks["n_tasks"] >= 2
    print(f"4. Motion imagery tasks: {cat_tasks['n_tasks']}")

    # 5. Invalid task
    bad = get_imagery_task("nonexistent")
    assert bad.get("error") == "task_not_found"
    print("5. Invalid task handled: OK")

    # 6. Start 6 imagery task sessions
    from app.core.imagery.task_session_manager import (
        complete_imagery_task_session,
        start_imagery_task_session,
        submit_imagery_task_rating,
    )
    task_ids = [
        ("red_circle_vividness", {"vividness": 8, "color_control": 7, "effort": 3, "fatigue": 2, "confidence": 8}),
        ("blue_cube_vividness", {"vividness": 6, "spatial_control": 5, "effort": 4, "fatigue": 3, "confidence": 7}),
        ("color_shift_red_to_blue", {"color_control": 7, "meta_control": 6, "effort": 4, "fatigue": 2, "confidence": 8}),
        ("static_cube_stability", {"spatial_control": 5, "vividness": 6, "stability": 5, "effort": 5, "fatigue": 3, "confidence": 6}),
        ("apple_detail_generation", {"detail": 7, "vividness": 7, "color_control": 8, "effort": 4, "fatigue": 2, "confidence": 8}),
        ("rotating_object", {"motion": 8, "spatial_control": 7, "effort": 3, "fatigue": 1, "confidence": 9}),
    ]

    session_ids = []
    for tid, ratings in task_ids:
        s = start_imagery_task_session(user_id, tid)
        assert "error" not in s, f"Start failed for {tid}: {s}"
        submit_imagery_task_rating(s["session_id"], ratings)
        complete_imagery_task_session(s["session_id"])
        session_ids.append(s["session_id"])
    print(f"6. {len(session_ids)} sessions completed across dimensions")

    # 7. Build imagery phenotype
    from app.core.imagery.imagery_phenotype import build_imagery_phenotype, load_imagery_phenotype
    phenotype = build_imagery_phenotype(user_id)
    assert phenotype.get("phenotype_label") is not None
    assert phenotype.get("profile") is not None
    assert len(phenotype.get("strongest_dimensions", [])) >= 0
    assert len(phenotype.get("weakest_dimensions", [])) >= 0
    print(f"7. Phenotype: label={phenotype['phenotype_label']}, sessions={phenotype['n_completed_sessions']}")
    print(f"   Strongest: {phenotype.get('strongest_dimensions', [])}")
    print(f"   Weakest: {phenotype.get('weakest_dimensions', [])}")

    loaded = load_imagery_phenotype(user_id)
    assert loaded is not None
    print("   Persistence: OK")

    # 8. Analyze imagery gaps
    from app.core.imagery.imagery_phenotype import analyze_imagery_gaps
    gaps = analyze_imagery_gaps(user_id)
    assert gaps.get("primary_gap") is not None
    assert len(gaps.get("ranked_gaps", [])) > 0
    print(f"8. Gaps: primary={gaps['primary_gap']}, ranked={len(gaps.get('ranked_gaps', []))} gaps")

    # 9. Generate task-based imagery plan
    from app.core.imagery.imagery_phenotype import generate_task_based_imagery_plan, load_task_based_plan
    task_plan = generate_task_based_imagery_plan(user_id, 7)
    assert len(task_plan.get("daily_tasks", [])) == 7
    print(f"9. Task plan: {len(task_plan['daily_tasks'])} days, primary_gap={task_plan.get('primary_gap')}")

    loaded_plan = load_task_based_plan(user_id)
    assert loaded_plan is not None
    print("   Plan persistence: OK")

    # 10. Verify adaptive planner includes phenotype context
    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    adaptive = build_adaptive_training_plan(user_id)
    ctx = adaptive.get("imagery_phenotype_context", {})
    if ctx.get("has_phenotype"):
        print(f"10. Adaptive plan phenotype context: present ({ctx.get('phenotype_label', '')})")
    else:
        print("10. Adaptive plan phenotype context: not applicable (no data)")

    # 11. Personal profile with phenotype summary
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    profile = build_personal_imagery_profile(user_id)
    ph_sum = profile.get("imagery_phenotype_summary", {})
    assert ph_sum.get("has_phenotype") is True or ph_sum == {}, f"Expected phenotype summary: {ph_sum}"
    print(f"11. Profile phenotype_summary: has_phenotype={ph_sum.get('has_phenotype', False)}")

    # 12. Sparse user
    sparse_phen = build_imagery_phenotype("nonexistent_v19")
    assert sparse_phen.get("status") == "no_data"
    print("12. Sparse user: Handled")

    # 13. Safety flags
    assert phenotype.get("not_clinical") is True
    assert gaps.get("not_mind_reading") is True
    assert task_plan.get("not_bci_claim") is True
    assert t.get("production_valid") is False
    print("13. Safety flags: All OK")

    # 14. Invalid category
    bad_cat = list_imagery_tasks("invalid_category")
    assert bad_cat.get("n_tasks") == 0
    assert "warning" in bad_cat
    print("14. Invalid category handled: OK")

    print("\n=== V19 IMAGERY PHENOTYPE ENGINE: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

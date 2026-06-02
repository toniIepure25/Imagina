"""V13 PID v2 Calibration — Integration Test."""

import sys

from app.core.calibration.pid_v2_calibration import (
    aggregate_pid_v2_history,
    compute_pid_v2,
    get_reference_task,
    list_reference_tasks,
    start_calibration_session,
    submit_imagery_rating,
    submit_reference_rating,
)


def main():
    print("=== V13 PID v2 CALIBRATION ===\n")

    # 1. List tasks
    tasks = list_reference_tasks()
    print(f"1. Reference tasks: {len(tasks)}")
    assert len(tasks) >= 8
    for t in tasks[:3]:
        print(f"   - {t['id']} (L{t.get('difficulty_level', 1)})")

    # 2. Start session
    s = start_calibration_session("default", "simple_red_circle_reference")
    assert "error" not in s, f"Failed to start: {s}"
    sid = s["session_id"]
    assert s["status"] == "reference_phase"
    print(f"2. Session started: {sid[:12]}...")

    # 3. Submit reference rating
    ref = {"clarity": 8, "detail": 7, "color_strength": 9, "spatial_stability": 6}
    s = submit_reference_rating(sid, ref)
    assert s["status"] == "imagery_phase"
    print("3. Reference rated: clarity=8")

    # 4. Invalid transition test
    err = submit_reference_rating(sid, ref)
    assert "error" in err, "Should reject invalid transition"
    print(f"4. Invalid transition caught: {err['error']}")

    # 5. Submit imagery rating
    img = {"clarity": 6, "detail": 5, "color_strength": 7, "spatial_stability": 5,
           "effort": 4, "fatigue": 3, "confidence": 7, "reconstruction_similarity": 6}
    s = submit_imagery_rating(sid, img)
    assert s["status"] == "completed"
    assert s.get("pid_v2") is not None
    pid = s["pid_v2"]["pid_v2"]
    assert 0 <= pid <= 1
    print(f"5. PID v2 computed: {pid:.3f} (similarity={s['pid_v2']['perception_similarity_score']:.3f})")
    print(f"   Gaps: {', '.join(f'{k}={v:.3f}' for k,v in s['pid_v2']['subscores'].items())}")
    print(f"   Interpretation: {s['pid_v2']['interpretation']}")

    # 6. PID summary
    summary = aggregate_pid_v2_history("default")
    print(f"6. PID summary: {summary['n_sessions']} sessions, mean={summary.get('mean_pid_v2', 'N/A')}")
    assert summary["not_clinical"] is True

    # 7. Sparse data
    empty = aggregate_pid_v2_history("nonexistent_user")
    assert empty["n_sessions"] == 0
    print(f"7. Sparse data: handled ({empty['status']})")

    # 8. Direct PID v2 computation
    task = get_reference_task("simple_red_circle_reference")
    direct = compute_pid_v2(ref, img, task)
    assert 0 <= direct["pid_v2"] <= 1
    print(f"8. Direct PID v2: {direct['pid_v2']:.3f}")

    print("\n=== V13 PID v2 CALIBRATION: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

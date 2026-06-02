"""V23 Protocol Studio — Integration Test."""

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
        s = {"session_id": sid, "user_id": user_id, "task": {"id": "simple_red_circle_reference", "target_dimensions": ["color","shape","spatial_position"]}, "status": "completed", "started_at": f"2026-12-{(i+1)*4:02d}T12:00:00Z", "reference_rating": {"clarity":8,"detail":7,"color_strength":9,"spatial_stability":6}, "imagery_rating": {"clarity":max(1,7-i),"detail":max(1,6-i),"color_strength":max(1,8-i),"spatial_stability":max(1,6-i),"effort":3,"fatigue":2,"confidence":7}, "pid_v2": {"pid_v2":pv,"subscores":{"clarity_gap":0.12,"detail_gap":0.15,"color_gap":0.10,"spatial_gap":0.08,"emotional_gap":0.02},"reliability":{"confidence":0.7}},"not_clinical":True}
        sd = os.path.join(CALIB_DIR, sid)
        os.makedirs(sd, exist_ok=True)
        json.dump(s, open(os.path.join(sd,"manifest.json"),"w"), indent=2, default=str)


def main():
    print("=== V23 IMAGERY PROTOCOL STUDIO ===\n")
    user_id = "v23_test"
    _ensure_data(user_id)

    from app.core.imagery.protocol_library import get_builtin_protocol_library, instantiate_builtin_protocol
    lib = get_builtin_protocol_library()
    assert lib["n_protocols"] >= 8
    print(f"1. Library: {lib['n_protocols']} built-in protocols")

    proto = instantiate_builtin_protocol(user_id, "baseline_imagery_assessment_7d")
    pid = proto["protocol_id"]
    assert proto.get("protocol_id") is not None
    print(f"2. Instantiated: {proto['title']} ({pid[:12]}...)")

    from app.core.imagery.protocol_studio import (
        analyze_protocol_run,
        compare_protocol_runs,
        complete_protocol_block,
        complete_protocol_run,
        export_imagina_benchmark_pack,
        start_next_protocol_block,
        start_protocol_run,
        validate_imagery_protocol,
    )

    valid = validate_imagery_protocol(proto)
    assert valid.get("valid") is True
    print("3. Validation: passed")

    run = start_protocol_run(user_id, pid)
    rid = run["run_id"]
    assert run["status"] == "active"
    total = run["progress"]["total_blocks"]
    print(f"4. Run started: {total} blocks")

    from app.core.imagery.guided_session_runtime import complete_guided_session, submit_guided_micro_checkin

    session_ids = []
    for i in range(min(3, total)):
        blk = start_next_protocol_block(rid)
        gs = blk.get("session", {})
        sid = gs.get("session_id", "")
        assert sid, f"No session from block {i}"
        submit_guided_micro_checkin(sid, {"vividness": 6, "stability": 5, "effort": 4, "fatigue": 3, "confidence": 7, "discomfort": 1})
        submit_guided_micro_checkin(sid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
        complete_guided_session(sid)
        complete_protocol_block(rid, sid)
        session_ids.append(sid)
    print(f"5. {len(session_ids)} blocks completed (sessions: {[s[:8] for s in session_ids]})")

    run = complete_protocol_run(rid)
    assert run["status"] == "completed"
    print(f"6. Run completed: {run['progress']['completed_blocks']}/{run['progress']['total_blocks']}")

    bench = analyze_protocol_run(rid)
    assert bench.get("metric_summary", {}).get("avg_iqi_proxy") is not None
    print(f"7. Benchmark: IQI={bench['metric_summary'].get('avg_iqi_proxy',0):.2f}, fatigue={bench['metric_summary'].get('avg_fatigue',0):.1f}")
    print(f"   Rec: {bench.get('recommended_next_protocol','')}")

    # Start another run for comparison
    proto2 = instantiate_builtin_protocol(user_id, "vividness_foundation_7d")
    run2 = start_protocol_run(user_id, proto2["protocol_id"])
    rid2 = run2["run_id"]
    for i in range(2):
        blk = start_next_protocol_block(rid2)
        sid = blk.get("session", {}).get("session_id", "")
        if sid:
            submit_guided_micro_checkin(sid, {"vividness":8,"stability":7,"effort":3,"fatigue":2,"confidence":9,"discomfort":1})
            complete_guided_session(sid)
            complete_protocol_block(rid2, sid)
    complete_protocol_run(rid2)

    comp = compare_protocol_runs(user_id, [rid, rid2])
    assert comp.get("winner_run_id") is not None
    print(f"8. Comparison: winner={comp.get('winner_run_id','')[:12]}..., ranked={len(comp.get('ranked_protocols',[]))}")

    exp = export_imagina_benchmark_pack(user_id, rid)
    assert exp.get("n_files", 0) >= 5
    print(f"9. Export: {exp['n_files']} files at {exp.get('export_dir','')[:50]}...")
    for f in exp.get("files", []):
        content = open(f).read()
        assert "raw_eeg" not in content.lower()
    print("   No raw EEG in export: OK")

    assert proto.get("not_clinical") is True
    assert bench.get("not_bci_claim") is True
    print("10. Safety flags: All OK")

    print("\n=== V23 IMAGERY PROTOCOL STUDIO: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""IMAGINA V23 — Protocol Studio + Execution Engine + Benchmark Analyzer + Comparator + Export."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
PROTOCOL_DIR = os.path.join(BASE, "protocols_v23")
RUN_DIR = os.path.join(BASE, "protocol_runs_v23")
COMPARE_DIR = os.path.join(BASE, "protocol_comparisons")
EXPORT_BASE = os.path.join(BASE, "benchmark_exports")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
    "visualization_boundary": ("Scene visualization is a symbolic training aid based on self-report proxies. "
                                "It is not a reconstruction of mental imagery, neural activity, dreams, or thoughts."),
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _append_jsonl(p, entry):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ─── PROTOCOL STUDIO ────────────────────────────────────────────

def create_imagery_protocol(user_id, payload):
    protocol_id = str(uuid4())
    protocol = {
        "protocol_id": protocol_id, "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": payload.get("title", "Untitled Protocol"),
        "description": payload.get("description", ""),
        "protocol_type": payload.get("protocol_type", "training_block"),
        "target_dimensions": payload.get("target_dimensions", []),
        "difficulty_range": payload.get("difficulty_range", [1, 3]),
        "duration_days": payload.get("duration_days", 7),
        "daily_structure": payload.get("daily_structure", []),
        "measurement_plan": payload.get("measurement_plan", {
            "primary_metric": "iqi_proxy",
            "secondary_metrics": ["pid_proxy", "stability_proxy", "fatigue", "confidence"],
            "skill_dimensions": [], "scene_metrics": ["clarity_delta", "fog_delta", "stability_delta"],
        }),
        "safety_policy": payload.get("safety_policy", {
            "stop_if_discomfort_gte": 8, "pause_if_fatigue_gte": 8,
            "reduce_difficulty_if_effort_gte": 8,
        }),
        **SAFETY,
    }
    d = os.path.join(PROTOCOL_DIR, protocol_id)
    _save_json(os.path.join(d, "protocol.json"), protocol)
    idx = _load_json(os.path.join(PROTOCOL_DIR, f"{user_id}_index.json")) or {"protocol_ids": []}
    idx["protocol_ids"].append(protocol_id)
    _save_json(os.path.join(PROTOCOL_DIR, f"{user_id}_index.json"), idx)
    return protocol


def get_imagery_protocol(protocol_id):
    p = os.path.join(PROTOCOL_DIR, protocol_id, "protocol.json")
    return _load_json(p)


def list_imagery_protocols(user_id):
    idx = _load_json(os.path.join(PROTOCOL_DIR, f"{user_id}_index.json"))
    if not idx:
        return []
    protocols = []
    for pid in idx.get("protocol_ids", []):
        p = get_imagery_protocol(pid)
        if p:
            protocols.append(p)
    return sorted(protocols, key=lambda x: x.get("created_at", ""), reverse=True)


def validate_imagery_protocol(payload):
    warnings = []
    if not payload.get("title"):
        warnings.append("missing_title")
    if not payload.get("daily_structure"):
        warnings.append("missing_daily_structure")
    from app.core.imagery.task_battery import get_imagery_task
    for day in payload.get("daily_structure", []):
        for block in day.get("blocks", []):
            task = get_imagery_task(block.get("task_id", ""))
            if task.get("error"):
                warnings.append(f"invalid_task_id: {block.get('task_id')}")
    return {"valid": len(warnings) == 0, "warnings": warnings, **SAFETY}


def delete_imagery_protocol(protocol_id):
    p = os.path.join(PROTOCOL_DIR, protocol_id, "protocol.json")
    if os.path.exists(p):
        os.remove(p)
        return {"status": "deleted", **SAFETY}
    return {"error": "not_found", **SAFETY}


# ─── PROTOCOL EXECUTION ENGINE ──────────────────────────────────

def start_protocol_run(user_id, protocol_id):
    p = get_imagery_protocol(protocol_id)
    if not p:
        return {"error": "protocol_not_found", **SAFETY}

    run_id = str(uuid4())
    total_blocks = sum(len(day.get("blocks", [])) for day in p.get("daily_structure", []))
    run = {
        "run_id": run_id, "user_id": user_id, "protocol_id": protocol_id,
        "protocol_title": p.get("title", ""),
        "status": "active", "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None, "current_day": 1, "current_block_index": 0,
        "completed_blocks": [], "active_session_id": None,
        "linked_guided_session_ids": [], "linked_scene_replay_ids": [],
        "progress": {"total_blocks": total_blocks, "completed_blocks": 0, "completion_rate": 0},
        **SAFETY,
    }
    d = os.path.join(RUN_DIR, run_id)
    _save_json(os.path.join(d, "manifest.json"), run)
    idx = _load_json(os.path.join(RUN_DIR, f"{user_id}_index.json")) or {"run_ids": []}
    idx["run_ids"].append(run_id)
    _save_json(os.path.join(RUN_DIR, f"{user_id}_index.json"), idx)
    return run


def get_protocol_run(run_id):
    return _load_json(os.path.join(RUN_DIR, run_id, "manifest.json"))


def get_active_protocol_run(user_id):
    idx = _load_json(os.path.join(RUN_DIR, f"{user_id}_index.json"))
    if not idx:
        return None
    for rid in reversed(idx.get("run_ids", [])):
        r = get_protocol_run(rid)
        if r and r.get("status") == "active":
            return r
    return None


def list_protocol_runs(user_id):
    idx = _load_json(os.path.join(RUN_DIR, f"{user_id}_index.json"))
    if not idx:
        return []
    runs = []
    for rid in idx.get("run_ids", []):
        r = get_protocol_run(rid)
        if r:
            runs.append(r)
    return sorted(runs, key=lambda x: x.get("started_at", ""), reverse=True)


def start_next_protocol_block(run_id):
    run = get_protocol_run(run_id)
    if not run or run.get("status") != "active":
        return {"error": "run_not_active", **SAFETY}

    p = get_imagery_protocol(run.get("protocol_id", ""))
    if not p:
        return {"error": "protocol_not_found", **SAFETY}

    daily = p.get("daily_structure", [])
    day_idx = run.get("current_day", 1) - 1
    block_idx = run.get("current_block_index", 0)
    if day_idx >= len(daily):
        return {"status": "protocol_complete", "message": "All days completed.", **SAFETY}

    blocks = daily[day_idx].get("blocks", [])
    if block_idx >= len(blocks):
        run["current_day"] += 1
        run["current_block_index"] = 0
        _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
        return start_next_protocol_block(run_id)

    block = blocks[block_idx]
    from app.core.imagery.guided_session_runtime import start_guided_imagery_session
    gs = start_guided_imagery_session(run["user_id"], block["task_id"], "protocol_run")
    if gs.get("error"):
        return gs

    run["active_session_id"] = gs["session_id"]
    run["linked_guided_session_ids"].append(gs["session_id"])
    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    _append_jsonl(os.path.join(RUN_DIR, run_id, "events.jsonl"),
                  {"event": "block_started", "run_id": run_id, "session_id": gs["session_id"],
                   "day": run["current_day"], "block_index": block_idx,
                   "timestamp": datetime.now(timezone.utc).isoformat()})
    return {"run": run, "session": gs, **SAFETY}


def complete_protocol_block(run_id, session_id):
    run = get_protocol_run(run_id)
    if not run or run.get("status") != "active":
        return {"error": "run_not_active", **SAFETY}

    run["completed_blocks"].append({"day": run["current_day"], "block_index": run["current_block_index"],
                                     "session_id": session_id})
    run["current_block_index"] += 1
    run["active_session_id"] = None
    total = run["progress"]["total_blocks"]
    done = len(run["completed_blocks"])
    run["progress"] = {"total_blocks": total, "completed_blocks": done,
                        "completion_rate": round(done / max(total, 1), 3)}

    try:
        from app.core.imagery.scene_simulator import get_guided_session_replay
        replay = get_guided_session_replay(session_id)
        if replay:
            run.setdefault("linked_scene_replay_ids", []).append(replay.get("replay_id", ""))
    except Exception:
        pass

    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    _append_jsonl(os.path.join(RUN_DIR, run_id, "events.jsonl"),
                  {"event": "block_completed", "run_id": run_id, "session_id": session_id,
                   "timestamp": datetime.now(timezone.utc).isoformat()})

    if done >= total:
        run["status"] = "completed"
        run["completed_at"] = datetime.now(timezone.utc).isoformat()
        _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
        _append_jsonl(os.path.join(RUN_DIR, run_id, "events.jsonl"),
                      {"event": "run_completed", "run_id": run_id,
                       "timestamp": run["completed_at"]})
    return run


def pause_protocol_run(run_id):
    run = get_protocol_run(run_id)
    if not run or run.get("status") != "active":
        return {"error": "run_not_active", **SAFETY}
    run["status"] = "paused"
    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    return run


def resume_protocol_run(run_id):
    run = get_protocol_run(run_id)
    if not run or run.get("status") != "paused":
        return {"error": "run_not_paused", **SAFETY}
    run["status"] = "active"
    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    return run


def complete_protocol_run(run_id):
    run = get_protocol_run(run_id)
    if not run or run.get("status") not in ("active", "paused"):
        return {"error": "run_not_active", **SAFETY}
    run["status"] = "completed"
    run["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    return run


def abort_protocol_run(run_id, reason=""):
    run = get_protocol_run(run_id)
    if not run or run.get("status") in ("completed", "aborted"):
        return {"error": "run_already_finalized", **SAFETY}
    run["status"] = "aborted"
    run["completed_at"] = datetime.now(timezone.utc).isoformat()
    run["abort_reason"] = reason
    _save_json(os.path.join(RUN_DIR, run_id, "manifest.json"), run)
    return run


# ─── BENCHMARK ANALYZER + COMPARATOR ────────────────────────────

def analyze_protocol_run(run_id):
    run = get_protocol_run(run_id)
    if not run:
        return {"error": "run_not_found", **SAFETY}

    sessions = run.get("linked_guided_session_ids", [])
    iqis, pids, stabs, fatigs, confs, clarities, fogs = [], [], [], [], [], [], []
    for sid in sessions:
        try:
            from app.core.imagery.guided_session_runtime import get_guided_session
            gs = get_guided_session(sid)
            if gs:
                sm = gs.get("final_summary") or {}
                iqis.append(sm.get("final_iqi_proxy", 0.5))
                pids.append(sm.get("final_pid_proxy", 0.5))
                fatigs.append(sm.get("avg_fatigue", 3))
                confs.append(sm.get("avg_confidence", 7))
                stabs.append(sm.get("avg_stability", 5))
        except Exception:
            pass
        try:
            from app.core.imagery.scene_simulator import get_scene_control_summary
            sc = get_scene_control_summary(sid)
            t = sc.get("scene_trend", {})
            clarities.append(t.get("clarity_delta", 0))
            fogs.append(t.get("fog_delta", 0))
        except Exception:
            pass

    n = len(iqis)
    if n == 0:
        return {"run_id": run_id, "n_blocks_completed": 0, "status": "no_data", **SAFETY}

    def _avg(arr):
        return round(sum(arr) / n, 3) if arr else 0
    passed = sum(1 for iq in iqis if iq >= 0.55)
    metric = {
        "avg_iqi_proxy": _avg(iqis), "avg_pid_proxy": _avg(pids),
        "avg_stability_proxy": _avg(stabs), "avg_fatigue": _avg(fatigs),
        "avg_confidence": _avg(confs),
    }

    best_idx = iqis.index(max(iqis)) if iqis else -1
    hardest_idx = iqis.index(min(iqis)) if iqis else -1

    report = {
        "run_id": run_id, "protocol_id": run.get("protocol_id", ""),
        "user_id": run.get("user_id", ""),
        "n_blocks_completed": len(run.get("completed_blocks", [])),
        "completion_rate": run.get("progress", {}).get("completion_rate", 0),
        "primary_metric": "iqi_proxy",
        "metric_summary": metric,
        "scene_summary": {"avg_clarity_delta": _avg(clarities), "avg_fog_delta": _avg(fogs)},
        "success_criteria_result": {
            "passed": passed >= n * 0.5,
            "passed_blocks": passed, "failed_blocks": n - passed,
            "reasons": [f"{passed}/{n} blocks met min IQI >= 0.55"],
        },
        "best_task_session": sessions[best_idx] if best_idx >= 0 else "",
        "hardest_task_session": sessions[hardest_idx] if hardest_idx >= 0 else "",
        "fatigue_bottleneck": _avg(fatigs) >= 6,
        "recommended_next_protocol": _rec_next(metric),
        **SAFETY,
    }
    d = os.path.join(RUN_DIR, run_id)
    _save_json(os.path.join(d, "benchmark_report.json"), report)
    return report


def _rec_next(metric):
    if metric.get("avg_fatigue", 5) >= 6:
        return "recovery_low_fatigue_5d"
    if metric.get("avg_iqi_proxy", 0.5) >= 0.65:
        return "stability_under_load_7d"
    if metric.get("avg_iqi_proxy", 0.5) < 0.45:
        return "vividness_foundation_7d"
    return "multisensory_integration_7d"


def compare_protocol_runs(user_id, run_ids):
    from app.core.imagery.protocol_studio import analyze_protocol_run as analyze
    analyses = []
    for rid in run_ids:
        a = analyze(rid)
        if not a.get("error"):
            analyses.append({"run_id": rid, "analysis": a})

    if len(analyses) < 2:
        return {"error": "need_at_least_2_runs", **SAFETY}

    def score(a):
        m = a["analysis"].get("metric_summary", {})
        return round(m.get("avg_iqi_proxy", 0.5) * 0.30 +
                     a["analysis"].get("completion_rate", 0) * 0.20 +
                     (1 - m.get("avg_pid_proxy", 0.5)) * 0.15 +
                     (1 - m.get("avg_fatigue", 5) / 10) * 0.15 +
                     abs(a["analysis"].get("scene_summary", {}).get("avg_clarity_delta", 0)) * 0.10 +
                     abs(a["analysis"].get("scene_summary", {}).get("avg_fog_delta", 0)) * 0.10, 3)

    ranked = sorted(analyses, key=score, reverse=True)
    result = {
        "comparison_id": str(uuid4()), "user_id": user_id, "run_ids": run_ids,
        "ranked_protocols": [{"run_id": r["run_id"], "protocol_id": r["analysis"].get("protocol_id", ""),
                               "score": score(r), "rank": i + 1} for i, r in enumerate(ranked)],
        "winner_run_id": ranked[0]["run_id"],
        "winner_protocol_id": ranked[0]["analysis"].get("protocol_id", ""),
        "recommendation": f"Protocol {ranked[0]['analysis'].get('protocol_id','')[:8]} performed best with score {score(ranked[0]):.2f}",
        **SAFETY,
    }
    d = os.path.join(COMPARE_DIR, user_id)
    _save_json(os.path.join(d, "latest_comparison.json"), result)
    return result


# ─── BENCHMARK EXPORT ───────────────────────────────────────────

def export_imagina_benchmark_pack(user_id, run_id=None):
    from app.core.imagery.protocol_studio import analyze_protocol_run, get_active_protocol_run, get_protocol_run
    if not run_id:
        active = get_active_protocol_run(user_id)
        if not active:
            runs = list_protocol_runs(user_id)
            run_id = runs[0]["run_id"] if runs else None
    if not run_id:
        return {"error": "no_run_found", **SAFETY}

    run = get_protocol_run(run_id)
    p = get_imagery_protocol(run.get("protocol_id", "")) if run else None
    analysis = analyze_protocol_run(run_id)

    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(EXPORT_BASE, user_id, f"{ts}_{run_id[:8]}")
    os.makedirs(ed, exist_ok=True)

    files = []
    for name, data in [
        ("manifest.json", {"export_id": str(uuid4()), "user_id": user_id, "run_id": run_id,
                            "generated_at": ts, "n_files": 0}),
        ("protocol.json", p or {}), ("protocol_run.json", run or {}),
        ("benchmark_report.json", analysis),
        ("safety_boundaries.json", SAFETY),
        ("README.md", f"""# IMAGINA Benchmark Export

**Protocol**: {p.get('title', '') if p else ''}
**Status**: {run.get('status', '') if run else ''}

## What Was Measured
- Self-report IQI/PID proxy metrics
- Session completion and adherence
- Scene clarity/fog/stability visual trends
- Protocol block completion

## What Was NOT Measured
- No EEG or neural data was collected or exported
- No raw free notes were exported
- No clinical, diagnostic, or therapeutic claims are made
- No mental image reconstruction was performed

## Interpretation
All metrics are personal exploratory self-report proxies.
Results apply to the individual user only.
This is not clinical evidence or validated neurofeedback.
"""),
    ]:
        path = os.path.join(ed, name)
        if isinstance(data, str):
            with open(path, "w") as f:
                f.write(data)
        else:
            _save_json(path, data)
        files.append(path)

    try:
        from app.core.imagery.skill_tree import load_skill_model
        sk = load_skill_model(user_id)
        if sk:
            pth = os.path.join(ed, "skill_model_summary.json")
            _save_json(pth, sk)
            files.append(pth)
    except Exception:
        pass

    try:
        from app.core.imagery.imagery_phenotype import load_imagery_phenotype
        ph = load_imagery_phenotype(user_id)
        if ph:
            pth = os.path.join(ed, "phenotype_summary.json")
            _save_json(pth, ph)
            files.append(pth)
    except Exception:
        pass

    try:
        from app.core.imagery.scene_simulator import export_guided_session_replay_summary
        for sid in (run.get("linked_guided_session_ids") or [])[:3]:
            rep = export_guided_session_replay_summary(sid)
            if rep:
                pth = os.path.join(ed, f"scene_replay_{sid[:8]}.json")
                _save_json(pth, rep)
                files.append(pth)
    except Exception:
        pass

    return {
        "export_id": str(uuid4()), "user_id": user_id, "run_id": run_id,
        "export_dir": ed, "files": files, "n_files": len(files), **SAFETY,
    }

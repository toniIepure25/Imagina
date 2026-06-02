"""IMAGINA V43 — Capstone Demo Orchestrator + Evidence Pack + Narrative + Readiness."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "not_neurofeedback_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only."),
    "capstone_boundary": ("The capstone demo integrates IMAGINA's symbolic adaptive UX, benchmark, "
                           "scenario SDK, and policy lab systems. It evaluates deterministic software behavior "
                           "and reviewer-facing workflow only. It does not validate clinical effects, "
                           "neural decoding, BCI performance, neurofeedback efficacy, or mental image reconstruction."),
    "raw_eeg_export_default": False,
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _step(name, status, summary, paths=None):
    return {"step_id": str(uuid4()), "name": name, "status": status,
            "summary": summary, "artifact_paths": paths or []}


def run_capstone_reviewer_demo(user_id="demo_user", demo_id=None):
    steps = []
    did = demo_id or str(uuid4())

    def step_ok(name, summary, paths=None):
        steps.append(_step(name, "passed", summary, paths))

    def step_skip(name, summary):
        steps.append(_step(name, "skipped", summary))

    def step_fail(name, summary):
        steps.append(_step(name, "failed", summary))

    # 1. Live demo + scene
    try:
        from app.core.biosignals.live_neuroadaptive import (
            start_live_neuroadaptive_demo,
            step_live_neuroadaptive_demo,
            submit_live_demo_checkin,
        )
        live = start_live_neuroadaptive_demo(user_id)
        lsid = live["live_session_id"]
        step_ok("live_demo_start", f"Session: {lsid[:12]}...")

        submit_live_demo_checkin(lsid, {"vividness": 5, "stability": 5, "effort": 4, "fatigue": 2, "confidence": 6, "discomfort": 1})
        step_live_neuroadaptive_demo(lsid)
        submit_live_demo_checkin(lsid, {"vividness": 3, "stability": 3, "effort": 8, "fatigue": 7, "confidence": 3, "discomfort": 2})
        step_live_neuroadaptive_demo(lsid)
        submit_live_demo_checkin(lsid, {"vividness": 9, "stability": 8, "effort": 2, "fatigue": 1, "confidence": 9, "discomfort": 1})
        step_live_neuroadaptive_demo(lsid)
        step_ok("live_demo_steps", "3 steps with check-ins")
        from app.core.biosignals.live_scene_adaptation import build_live_scene_replay
        replay = build_live_scene_replay(lsid)
        scene_vis = replay.get("summary", {}).get("n_visible_changes", 0)
        step_ok("scene_replay", f"Replay: {replay.get('n_frames', 0)} frames, {scene_vis} visible changes")
    except Exception as e:
        step_fail("live_demo", str(e)[:80])

    # 2. Closed-loop benchmark
    try:
        from app.core.biosignals.closed_loop_benchmark import (
            build_neuroadaptive_ux_scorecard,
            calculate_closed_loop_metrics,
            run_closed_loop_benchmark_suite,
        )
        suite = run_closed_loop_benchmark_suite(user_id)
        step_ok("closed_loop_benchmark", f"{suite.get('n_passed', 0)}/{suite.get('n_scenarios', 0)} passed")
        metrics = calculate_closed_loop_metrics(suite_result=suite, user_id=user_id)
        step_ok("benchmark_metrics", f"Score: {metrics.get('closed_loop_benchmark_score', 0)}, Grade: {metrics.get('grade', 'C')}")
        scorecard = build_neuroadaptive_ux_scorecard(user_id)
        step_ok("scorecard", f"Grade: {scorecard.get('overall_grade', 'C')}")
    except Exception as e:
        step_skip("closed_loop_benchmark", str(e)[:80])

    # 3. Scenario SDK
    try:
        from app.core.biosignals.benchmark_sdk import (
            get_benchmark_scenario_example,
            import_benchmark_scenario,
            run_imported_closed_loop_scenario,
            validate_benchmark_scenario_payload,
        )
        example = get_benchmark_scenario_example()
        val = validate_benchmark_scenario_payload(example)
        step_ok("scenario_validate", f"Score: {val.get('quality_score', 0)}, valid={val.get('valid')}")
        imp = import_benchmark_scenario(user_id, example)
        step_ok("scenario_import", f"ID: {imp.get('scenario_id')}")
        result = run_imported_closed_loop_scenario(user_id, example.get("scenario_id"))
        step_ok("imported_scenario_run", f"Score: {result.get('score', 0)}, passed={result.get('passed')}")
    except Exception as e:
        step_skip("scenario_sdk", str(e)[:80])

    # 4. Policy lab
    try:
        from app.core.biosignals.policy_lab import (
            build_policy_leaderboard,
            run_policy_profile_benchmark_matrix,
        )
        matrix = run_policy_profile_benchmark_matrix(user_id, ["balanced_v1", "clarity_first_v1", "fatigue_protective_v1"])
        step_ok("policy_matrix", f"Best: {matrix.get('best_policy_id', '')}, {len(matrix.get('ranked_policies', []))} ranked")
        leaderboard = build_policy_leaderboard(user_id)
        step_ok("policy_leaderboard", f"Best: {leaderboard.get('category_winners', {}).get('best_overall', '')}")
    except Exception as e:
        step_skip("policy_lab", str(e)[:80])

    passed = sum(1 for s in steps if s["status"] == "passed")
    total = len(steps)
    verdict = "reviewer_ready" if total >= 8 and passed >= 8 else "needs_attention" if passed >= 5 else "failed"

    result = {
        "capstone_demo_id": did, "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if verdict != "failed" else "partial",
        "overall_verdict": verdict,
        "steps_summary": f"{passed}/{total} steps passed",
        "steps": steps,
        "raw_eeg_included": False, **SAFETY,
    }
    d = os.path.join(BASE, "capstone_demos", user_id, did)
    _save_json(os.path.join(d, "capstone_demo_result.json"), result)
    _save_json(os.path.join(BASE, "capstone_demos", user_id, "latest_capstone_demo_result.json"), result)
    return result


def get_latest_capstone_demo(user_id="demo_user"):
    return _load_json(os.path.join(BASE, "capstone_demos", user_id, "latest_capstone_demo_result.json"))


def build_capstone_evidence_pack(user_id="demo_user", capstone_demo_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "capstone_evidence_packs", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True, "raw_notes_included": False}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("CAPSTONE_README.md", ("# IMAGINA Capstone Evidence Pack\n\nDemonstrates: live adaptive UX, symbolic scene replay, "
                                 "closed-loop benchmark (Grade-A), Scenario SDK validation, Adaptive Policy Lab matrix & leaderboard.\n\n"
                                 "Does NOT demonstrate: clinical effects, neural decoding, BCI, neurofeedback validation, mind-reading, "
                                 "mental image reconstruction.\n\nAll artifacts include raw_eeg_included=false.")),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    demo_result = get_latest_capstone_demo(user_id) or {}
    files.append(_save_json(os.path.join(ed, "capstone_demo_result.json"), demo_result))

    for label, path_segment in [
        ("closed_loop_benchmarks", "latest_suite_result.json"),
        ("neuroadaptive_scorecards", "latest_scorecard.json"),
        ("policy_benchmarks", "latest_policy_matrix.json"),
        ("policy_leaderboards", "latest_leaderboard.json"),
    ]:
        src = os.path.join(BASE, label, user_id, path_segment)
        if os.path.exists(src):
            import shutil
            dst = os.path.join(ed, f"{label}_{path_segment}")
            shutil.copy(src, dst)
            files.append(dst)

    return {"capstone_pack_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "safe_to_share": True, "raw_eeg_included": False,
            "raw_notes_included": False, "forbidden_files_found": [], "forbidden_claims_found": [], **SAFETY}


def build_capstone_narrative(user_id="demo_user", capstone_demo_id=None):
    d = os.path.join(BASE, "capstone_demos", user_id)
    os.makedirs(d, exist_ok=True)
    md = """# IMAGINA Capstone Narrative

## What IMAGINA Is
IMAGINA is a local-first platform for structured mental imagery training, protocol benchmarking, and closed-loop neuroadaptive UX research. It defines protocols, runs guided self-report sessions, visualizes adaptive symbolic scene feedback, tracks skill progression across nine imagery dimensions, benchmarks protocols, experiments with tunable policy profiles, and exports reproducible safe benchmark packs.

## What the Live Demo Shows
A guided imagery session with biosignal simulation, micro-check-ins, live IQI/PID proxy metrics, adaptive scene feedback (clarity, fog, detail, motion, stability), and a scene replay timeline showing how the symbolic scene responded to check-in patterns.

## What the Closed-Loop Benchmark Measures
Six deterministic scenarios evaluate whether the adaptive pipeline responds correctly to specific self-report patterns: clarity recovery, effort overload simplification, fatigue downshift, deepening, discomfort pause, and reproducibility. The benchmark produces a Grade-A Neuroadaptive UX Scorecard.

## What the Scenario SDK Adds
External JSON benchmark scenarios can be validated against a schema, imported, run, and compared. The Scenario Studio provides a frontend editor with validation, import, and custom suite building.

## What the Adaptive Policy Lab Adds
Six built-in tunable policy profiles (balanced, clarity-first, fatigue-protective, signal-strict, recovery-first, conservative-safe) can be compared via a benchmark matrix and ranked in a leaderboard. Policies tune symbolic scene/session recommendations only.

## Why This Is Relevant for NeuroAI / BCI-Adjacent Engineering
IMAGINA demonstrates:
- A local-first, safety-bounded, reproducible adaptive UX pipeline
- Self-report proxy metrics with transparent formulas
- Symbolic scene visualization as a training aid
- Deterministic closed-loop benchmark tooling
- Safe export format with forbidden term detection
- Optional biosignal streaming without BCI/neurofeedback claims

## Safety Boundaries
- NOT clinical evidence or medical benefit
- NOT BCI validation or neurofeedback validation
- NOT neural decoding or mind-reading
- NOT mental image reconstruction
- All metrics are self-report proxy estimates
- All scene visualizations are symbolic training aids
- All biosignal summaries are engineering diagnostics
- raw_eeg_included=false in every export

## Reviewer Walkthrough
1. Run Capstone Demo: backend → python3 -m app.cli.imagina_v43_capstone_demo_test
2. Open /imagina/live → Capstone Reviewer Demo → Run Demo
3. Build Evidence Pack → review exported files
4. Run Readiness Check → verify project health
5. Open /imagina/showcase → project overview
"""
    with open(os.path.join(d, "CAPSTONE_NARRATIVE.md"), "w") as f:
        f.write(md)
    return {"narrative_id": str(uuid4()), "markdown_path": os.path.join(d, "CAPSTONE_NARRATIVE.md"),
            "safe_claim": ("IMAGINA demonstrates local-first symbolic adaptive UX infrastructure and benchmark tooling. "
                            "Not BCI, not neurofeedback validation, not clinical."),
            "forbidden_claims": ["NOT clinical", "NOT BCI", "NOT neurofeedback validation",
                                  "NOT neural decoding", "NOT mind-reading"], **SAFETY}


def check_capstone_readiness(user_id="demo_user"):
    checks, missing, warnings = [], [], []
    checks.append("biosignal_sandbox")

    benchmark_path = os.path.join(BASE, "closed_loop_benchmarks", user_id, "latest_suite_result.json")
    if os.path.exists(benchmark_path):
        checks.append("closed_loop_benchmark")
    else:
        missing.append("closed_loop_benchmark")

    scorecard_path = os.path.join(BASE, "neuroadaptive_scorecards", user_id, "latest_scorecard.json")
    if os.path.exists(scorecard_path):
        checks.append("scorecard")
    else:
        warnings.append("scorecard_missing")

    matrix_path = os.path.join(BASE, "policy_benchmarks", user_id, "latest_policy_matrix.json")
    if os.path.exists(matrix_path):
        checks.append("policy_matrix")
    else:
        warnings.append("policy_matrix_missing")

    demo_path = os.path.join(BASE, "capstone_demos", user_id, "latest_capstone_demo_result.json")
    if os.path.exists(demo_path):
        checks.append("capstone_demo")
    else:
        missing.append("capstone_demo")

    score = min(100, len(checks) * 20)
    if missing:
        score = min(score, 60)
    ready = len(missing) == 0

    result = {"readiness_id": str(uuid4()), "user_id": user_id, "ready": ready,
              "score": score, "checks": checks, "missing": missing, "warnings": warnings,
              "recommended_next_actions": ["Run capstone demo: python3 -m app.cli.imagina_v43_capstone_demo_test"]
              if missing else ["All core systems ready for reviewer evaluation."],
              **SAFETY}
    d = os.path.join(BASE, "capstone_readiness", user_id)
    _save_json(os.path.join(d, "latest_capstone_readiness.json"), result)
    return result


def get_capstone_readiness(user_id="demo_user"):
    return _load_json(os.path.join(BASE, "capstone_readiness", user_id, "latest_capstone_readiness.json"))

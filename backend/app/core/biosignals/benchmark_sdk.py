"""IMAGINA V37 — Benchmark Scenario SDK: Schema + Validator + I/O + Custom Suites + SDK Export."""

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
    "benchmark_sdk_boundary": ("External benchmark scenarios test software behavior and symbolic adaptation only. "
                                "They do not validate clinical, neural, BCI, or neurofeedback claims."),
    "raw_eeg_export_default": False,
}

FORBIDDEN_TERMS = ["clinical", "diagnosis", "therapy", "treatment", "cure", "BCI-ready",
                    "mind-reading", "dream decoding", "decode thoughts", "neural reconstruction",
                    "validated neurofeedback", "medical", "patient", "disorder"]

ALLOWED_DIRECTIONS = ["increase", "decrease", "any", "none"]
ALLOWED_TYPES = ["clarity", "fatigue", "effort", "discomfort", "signal_quality", "reproducibility", "custom"]
ALLOWED_POLICIES = ["clarity", "simplify", "pause", "recovery", "continue"]
ALLOWED_GATES = ["open", "caution", "degraded", "blocked", "any"]

SCHEMA_EXAMPLE = {
    "imagina_benchmark_scenario_version": "1.0",
    "scenario_id": "custom_clarity_recovery",
    "title": "Custom Clarity Recovery",
    "description": "Low vividness triggers clarity support; recovery increases clarity.",
    "author": "optional",
    "license": "personal",
    "scenario_type": "clarity",
    "purpose": "Verify clarity recovery behavior.",
    "checkins": [
        {"label": "baseline", "vividness": 5, "stability": 5, "effort": 4, "fatigue": 2, "confidence": 6, "discomfort": 1},
        {"label": "low_vividness", "vividness": 3, "stability": 4, "effort": 5, "fatigue": 3, "confidence": 4, "discomfort": 1},
        {"label": "recovery", "vividness": 8, "stability": 7, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1},
    ],
    "injected_conditions": {"force_gate_state": None, "source_type": "simulated_eeg", "signal_quality_override": None},
    "expected_outcomes": {
        "clarity_change": "increase", "fog_change": "any", "detail_change": "any",
        "motion_change": "any", "brightness_change": "any", "stability_change": "any",
        "policy_family": ["clarity"], "safety_gate": "any",
    },
    "pass_criteria": {"min_score": 60, "required_checks": ["scene_responsiveness"], "allow_partial_pass": True},
    "metadata": {"tags": ["demo"], "difficulty": "beginner", "expected_visible_change": True},
    "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ─── SCHEMA + VALIDATOR ─────────────────────────────────────────

def get_benchmark_scenario_schema():
    return {
        "imagina_benchmark_scenario_version": "1.0",
        "required_fields": ["scenario_id", "title", "checkins", "expected_outcomes", "pass_criteria", "boundaries"],
        "allowed_scenario_types": ALLOWED_TYPES,
        "allowed_directions": ALLOWED_DIRECTIONS,
        "allowed_policy_families": ALLOWED_POLICIES,
        "allowed_gates": ALLOWED_GATES,
        "forbidden_terms": FORBIDDEN_TERMS,
        **SAFETY,
    }


def get_benchmark_scenario_example():
    return SCHEMA_EXAMPLE


def validate_benchmark_scenario_payload(payload):
    errors, warnings, forbidden = [], [], []
    cat_scores = {"schema": 20, "checkin": 20, "expectation": 20, "safety": 25, "runnable": 15}
    text = json.dumps(payload).lower()
    for safe_phrase in ['not_clinical', 'not_diagnostic', 'not_mind_reading', 'not_bci_claim',
                          'not_bci', 'not_neurofeedback_claim', 'production_valid',
                          'scientific_boundary', 'benchmark_sdk_boundary', 'analysis_mode']:
        text = text.replace(safe_phrase, "")

    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            forbidden.append(term)
            cat_scores["safety"] = 0

    schema = get_benchmark_scenario_schema()
    for field in schema["required_fields"]:
        if field not in payload:
            errors.append(f"missing_{field}")
            cat_scores["schema"] = max(0, cat_scores["schema"] - 5)

    if payload.get("scenario_type", "") not in ALLOWED_TYPES:
        errors.append(f"invalid_type: {payload.get('scenario_type')}")
        cat_scores["schema"] = max(0, cat_scores["schema"] - 5)

    checkins = payload.get("checkins", [])
    if len(checkins) < 1:
        errors.append("no_checkins")
        cat_scores["runnable"] = 0
    if len(checkins) > 20:
        warnings.append("many_checkins")
    for ci in checkins:
        for k in ["vividness", "stability", "effort", "fatigue", "confidence", "discomfort"]:
            v = ci.get(k)
            if v is not None and (v < 1 or v > 10):
                warnings.append(f"checkin_{k}_out_of_range")
                cat_scores["checkin"] = max(0, cat_scores["checkin"] - 2)

    exp = payload.get("expected_outcomes", {})
    for k in ["clarity_change", "fog_change", "detail_change", "motion_change", "brightness_change", "stability_change"]:
        if exp.get(k, "any") not in ALLOWED_DIRECTIONS:
            warnings.append(f"invalid_direction_{k}")
            cat_scores["expectation"] = max(0, cat_scores["expectation"] - 3)
    for pf in exp.get("policy_family", []):
        if pf not in ALLOWED_POLICIES:
            warnings.append(f"invalid_policy_{pf}")
    if exp.get("safety_gate", "any") not in ALLOWED_GATES:
        warnings.append("invalid_gate")
        cat_scores["expectation"] = max(0, cat_scores["expectation"] - 3)

    boundaries = payload.get("boundaries", {})
    for k in ["not_clinical", "not_bci", "not_neurofeedback_claim", "not_mind_reading"]:
        if not boundaries.get(k):
            errors.append(f"boundary_missing_{k}")
            cat_scores["safety"] = max(0, cat_scores["safety"] - 5)

    quality = sum(cat_scores.values())
    if forbidden:
        quality = min(50, quality)

    return {
        "valid": len(errors) == 0 and not forbidden,
        "quality_score": quality,
        "category_scores": cat_scores,
        "warnings": warnings, "errors": errors,
        "forbidden_terms_found": forbidden,
        "runnable": len(errors) == 0 and len(checkins) >= 2,
        "safe_to_import": not forbidden and len(errors) == 0,
        "recommendations": ["Valid scenario." if not errors and not forbidden else "Fix errors before importing."],
        **SAFETY,
    }


# ─── IMPORT / EXPORT ────────────────────────────────────────────

def _scenario_dir(user_id, scenario_id):
    return os.path.join(BASE, "benchmark_scenarios", user_id, "scenarios", f"{scenario_id}.json")


def _registry_path(user_id):
    return os.path.join(BASE, "benchmark_scenarios", user_id, "registry.json")


def import_benchmark_scenario(user_id, scenario_payload, allow_draft=False):
    validation = validate_benchmark_scenario_payload(scenario_payload)
    if not validation["safe_to_import"] and not allow_draft:
        return {"error": "validation_failed", "validation": validation, **SAFETY}

    sid = scenario_payload.get("scenario_id", str(uuid4()))
    entry = {"scenario_id": sid, "user_id": user_id, "origin": "imported",
             "imported_at": datetime.now(timezone.utc).isoformat(),
             "valid": validation["valid"], "validation": validation,
             "payload": scenario_payload, **SAFETY}
    _save_json(_scenario_dir(user_id, sid), entry)
    reg = _load_json(_registry_path(user_id)) or {"scenarios": []}
    if sid not in reg["scenarios"]:
        reg["scenarios"].append(sid)
    _save_json(_registry_path(user_id), reg)
    return entry


def list_imported_benchmark_scenarios(user_id="demo_user"):
    reg = _load_json(_registry_path(user_id))
    if not reg:
        return {"scenarios": [], "n": 0, **SAFETY}
    results = []
    for sid in reg.get("scenarios", []):
        s = get_imported_benchmark_scenario(user_id, sid)
        if s:
            results.append(s)
    return {"scenarios": results, "n": len(results), **SAFETY}


def get_imported_benchmark_scenario(user_id, scenario_id):
    return _load_json(_scenario_dir(user_id, scenario_id))


def remove_imported_benchmark_scenario(user_id, scenario_id):
    p = _scenario_dir(user_id, scenario_id)
    if os.path.exists(p):
        os.remove(p)
        reg = _load_json(_registry_path(user_id)) or {}
        reg["scenarios"] = [s for s in reg.get("scenarios", []) if s != scenario_id]
        _save_json(_registry_path(user_id), reg)
    return {"status": "removed", **SAFETY}


def export_benchmark_scenario(user_id, scenario_id):
    s = get_imported_benchmark_scenario(user_id, scenario_id)
    if not s:
        return {"error": "not_found", **SAFETY}
    ed = os.path.join(BASE, "benchmark_scenarios", user_id, "exports")
    _save_json(os.path.join(ed, f"{scenario_id}.json"), s.get("payload", {}))
    return {"scenario_id": scenario_id, "exported_to": os.path.join(ed, f"{scenario_id}.json"), **SAFETY}


# ─── RUN IMPORTED SCENARIO ──────────────────────────────────────

def run_imported_closed_loop_scenario(user_id, scenario_id):
    s = get_imported_benchmark_scenario(user_id, scenario_id)
    if not s:
        return {"error": "not_found", **SAFETY}

    payload = s.get("payload", {})
    checkins = payload.get("checkins", [])

    from app.core.biosignals.live_neuroadaptive import (
        complete_live_neuroadaptive_demo,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )
    from app.core.biosignals.scene_dynamics_engine import build_live_scene_replay

    live = start_live_neuroadaptive_demo(user_id)
    lsid = live["live_session_id"]
    scenes = []
    policy_trace = []
    state_trace = []

    for ci in checkins:
        submit_live_demo_checkin(lsid, ci)
        f = step_live_neuroadaptive_demo(lsid)
        sa = f.get("scene_adaptation", {}).get("scene_after_preview", {})
        if sa:
            scenes.append(sa)
        policy_trace.append(f.get("policy_action", ""))
        state_trace.append(f.get("adaptive_state", ""))

    complete_live_neuroadaptive_demo(lsid)

    first = scenes[0] if scenes else {}
    last = scenes[-1] if scenes else {}
    exp = payload.get("expected_outcomes", {})

    def dir_check(direction, delta, tol=0.01):
        if direction == "increase":
            return delta > tol
        if direction == "decrease":
            return delta < -tol
        if direction == "none":
            return abs(delta) <= tol
        return True  # any

    checks = []
    score = 100
    for k in ["clarity_change", "fog_change", "detail_change", "motion_change", "brightness_change", "stability_change"]:
        direction = exp.get(k, "any")
        if direction != "any":
            key = k.replace("_change", "")
            key = {"fog": "fog", "clarity": "clarity", "detail": "detail_density", "motion": "motion_speed", "brightness": "brightness", "stability": "stability_anchor"}.get(key, key)
            delta = last.get(key, 0) - first.get(key, 0)
            passed = dir_check(direction, delta)
            checks.append({"check": k, "direction": direction, "delta": round(delta, 3), "passed": passed})
            if not passed:
                score -= 10

    pf_match = False
    for pf in exp.get("policy_family", []):
        mapping = {"clarity": "clarity", "simplify": "reduce", "pause": "pause", "recovery": "recovery", "continue": "continue"}
        kw = mapping.get(pf, pf)
        if any(kw in (p or "").lower() for p in policy_trace):
            pf_match = True
    if exp.get("policy_family") and not pf_match:
        score -= 10

    replay = build_live_scene_replay(lsid)
    n_vis = replay.get("summary", {}).get("n_visible_changes", 0) if replay else 0

    result = {
        "scenario_result_id": str(uuid4()),
        "scenario_id": scenario_id,
        "user_id": user_id,
        "scenario_origin": "imported",
        "passed": score >= payload.get("pass_criteria", {}).get("min_score", 60),
        "score": max(0, score),
        "n_steps": len(checkins),
        "live_session_id": lsid,
        "observed_metrics": {
            "clarity_change": round(last.get("clarity", 0) - first.get("clarity", 0), 3),
            "fog_change": round(last.get("fog", 0) - first.get("fog", 0), 3),
            "detail_change": round(last.get("detail_density", 0) - first.get("detail_density", 0), 3),
            "motion_change": round(last.get("motion_speed", 0) - first.get("motion_speed", 0), 3),
            "brightness_change": round(last.get("brightness", 0) - first.get("brightness", 0), 3),
            "n_visible_changes": n_vis,
        },
        "policy_trace": policy_trace,
        "state_trace": state_trace,
        "pass_fail_checks": checks,
        "failure_reasons": [c["check"] for c in checks if not c["passed"]],
        "validation_report": s.get("validation", {}),
        **SAFETY,
    }
    return result


# ─── CUSTOM SUITES ──────────────────────────────────────────────

def _suite_registry(user_id):
    return os.path.join(BASE, "custom_benchmark_suites", user_id, "registry.json")


def _suite_path(user_id, suite_id):
    return os.path.join(BASE, "custom_benchmark_suites", user_id, "suites", f"{suite_id}.json")


def create_custom_benchmark_suite(user_id, suite_name, scenario_ids, include_built_ins=True):
    sid = str(uuid4())
    suite = {"suite_id": sid, "user_id": user_id, "suite_name": suite_name,
             "created_at": datetime.now(timezone.utc).isoformat(),
             "scenario_ids": scenario_ids, "include_built_ins": include_built_ins, **SAFETY}
    _save_json(_suite_path(user_id, sid), suite)
    reg = _load_json(_suite_registry(user_id)) or {"suite_ids": []}
    reg["suite_ids"].append(sid)
    _save_json(_suite_registry(user_id), reg)
    return suite


def run_custom_benchmark_suite(user_id, suite_id):
    suite = _load_json(_suite_path(user_id, suite_id))
    if not suite:
        return {"error": "suite_not_found", **SAFETY}

    results = []
    if suite.get("include_built_ins"):
        from app.core.biosignals.closed_loop_benchmark import run_closed_loop_benchmark_scenario
        for s in ["clarity_recovery", "effort_overload_simplification", "fatigue_downshift"]:
            results.append(run_closed_loop_benchmark_scenario(user_id, s))

    for sid in suite.get("scenario_ids", []):
        results.append(run_imported_closed_loop_scenario(user_id, sid))

    passed = sum(1 for r in results if r.get("passed"))
    scores = [r["score"] for r in results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    pre = round(passed / len(results), 2) if results else 0

    suite_result = {
        "suite_id": suite_id, "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_scenarios": len(results), "n_passed": passed,
        "pass_rate": pre, "avg_score": avg_score,
        "scenario_results": results,
        "overall_verdict": "excellent" if avg_score >= 90 else "good" if avg_score >= 70 else "needs_attention",
        **SAFETY,
    }
    rd = os.path.join(BASE, "custom_benchmark_suites", user_id, "results")
    _save_json(os.path.join(rd, f"{suite_id}_latest_result.json"), suite_result)
    return suite_result


def list_custom_benchmark_suites(user_id="demo_user"):
    reg = _load_json(_suite_registry(user_id))
    if not reg:
        return {"suites": [], "n": 0, **SAFETY}
    results = []
    for sid in reg.get("suite_ids", []):
        s = _load_json(_suite_path(user_id, sid))
        if s:
            results.append(s)
    return {"suites": results, "n": len(results), **SAFETY}


def get_custom_benchmark_suite(user_id, suite_id):
    return _load_json(_suite_path(user_id, suite_id))


# ─── SDK EXPORT ─────────────────────────────────────────────────

def export_benchmark_sdk_pack(user_id="demo_user"):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "benchmark_sdk_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("benchmark_scenario_schema.json", json.dumps(get_benchmark_scenario_schema(), indent=2)),
        ("benchmark_scenario_example.json", json.dumps(SCHEMA_EXAMPLE, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Benchmark Scenario SDK Export\n\nExternal scenarios test software behavior only. No raw EEG. Not BCI. Not neurofeedback validation. Not clinical."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    imported = list_imported_benchmark_scenarios(user_id)
    bp = os.path.join(ed, "imported_scenarios.json")
    _save_json(bp, imported)
    files.append(bp)

    from app.core.biosignals.closed_loop_benchmark import get_closed_loop_benchmark_scenarios
    sp = os.path.join(ed, "built_in_scenarios.json")
    _save_json(sp, get_closed_loop_benchmark_scenarios())
    files.append(sp)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}

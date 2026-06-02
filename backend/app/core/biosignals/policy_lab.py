"""IMAGINA V40 — Adaptive Policy Lab: Schema + Validator + Registry + Benchmark + Leaderboard + Export."""

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
    "policy_lab_boundary": ("Adaptive policy profiles tune symbolic scene and session recommendations only. "
                             "They do not infer mental content, diagnose states, validate neurofeedback, "
                             "or provide BCI control."),
    "raw_eeg_export_default": False,
}

FORBIDDEN_TERMS = ["clinical", "diagnosis", "therapy", "treatment", "cure", "BCI-ready",
                    "mind-reading", "dream decoding", "decode thoughts", "neural reconstruction",
                    "validated neurofeedback", "medical", "patient", "disorder"]

BUILTIN_POLICIES = [
    {"policy_id": "balanced_v1", "title": "Balanced Policy",
     "description": "Default balanced weights across all scene and safety parameters.",
     "policy_type": "balanced",
     "weights": {"clarity_gain": 1.0, "fog_reduction": 1.0, "detail_gain": 1.0, "motion_gain": 1.0,
                  "fatigue_penalty": 1.0, "effort_penalty": 1.0, "discomfort_penalty": 1.0, "safety_priority": 1.0},
     "thresholds": {"fatigue_risk": 6, "effort_overload": 8, "discomfort_warning": 5,
                     "pause_recommended_fatigue": 8, "pause_recommended_discomfort": 7, "minimum_sqi_for_adaptation": 0.55},
     "scene_delta_limits": {"max_positive_delta": 0.15, "max_negative_delta": -0.15},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
    {"policy_id": "clarity_first_v1", "title": "Clarity First",
     "description": "Prioritizes clarity and detail gains; less conservative on fatigue.",
     "policy_type": "clarity_first",
     "weights": {"clarity_gain": 1.5, "fog_reduction": 1.4, "detail_gain": 1.3, "motion_gain": 1.0,
                  "fatigue_penalty": 0.7, "effort_penalty": 0.8, "discomfort_penalty": 1.0, "safety_priority": 0.8},
     "thresholds": {"fatigue_risk": 7, "effort_overload": 9, "discomfort_warning": 6,
                     "pause_recommended_fatigue": 9, "pause_recommended_discomfort": 8, "minimum_sqi_for_adaptation": 0.45},
     "scene_delta_limits": {"max_positive_delta": 0.18, "max_negative_delta": -0.12},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
    {"policy_id": "fatigue_protective_v1", "title": "Fatigue Protective",
     "description": "High fatigue/discomfort sensitivity; early recovery triggers.",
     "policy_type": "fatigue_protective",
     "weights": {"clarity_gain": 0.9, "fog_reduction": 0.8, "detail_gain": 0.8, "motion_gain": 0.7,
                  "fatigue_penalty": 1.8, "effort_penalty": 1.5, "discomfort_penalty": 2.0, "safety_priority": 1.5},
     "thresholds": {"fatigue_risk": 5, "effort_overload": 7, "discomfort_warning": 4,
                     "pause_recommended_fatigue": 7, "pause_recommended_discomfort": 6, "minimum_sqi_for_adaptation": 0.55},
     "scene_delta_limits": {"max_positive_delta": 0.10, "max_negative_delta": -0.15},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
    {"policy_id": "signal_strict_v1", "title": "Signal Strict",
     "description": "Requires high signal quality; minimal adaptation when degraded.",
     "policy_type": "signal_strict",
     "weights": {"clarity_gain": 0.8, "fog_reduction": 0.7, "detail_gain": 0.7, "motion_gain": 0.6,
                  "fatigue_penalty": 1.0, "effort_penalty": 1.0, "discomfort_penalty": 1.0, "safety_priority": 1.8},
     "thresholds": {"fatigue_risk": 6, "effort_overload": 8, "discomfort_warning": 5,
                     "pause_recommended_fatigue": 8, "pause_recommended_discomfort": 7, "minimum_sqi_for_adaptation": 0.75},
     "scene_delta_limits": {"max_positive_delta": 0.10, "max_negative_delta": -0.10},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
    {"policy_id": "recovery_first_v1", "title": "Recovery First",
     "description": "Quick to simplify/slow/pause; conservative scene deltas.",
     "policy_type": "recovery_first",
     "weights": {"clarity_gain": 0.6, "fog_reduction": 0.5, "detail_gain": 0.5, "motion_gain": 0.4,
                  "fatigue_penalty": 2.0, "effort_penalty": 1.8, "discomfort_penalty": 2.5, "safety_priority": 2.0},
     "thresholds": {"fatigue_risk": 4, "effort_overload": 6, "discomfort_warning": 3,
                     "pause_recommended_fatigue": 6, "pause_recommended_discomfort": 5, "minimum_sqi_for_adaptation": 0.55},
     "scene_delta_limits": {"max_positive_delta": 0.08, "max_negative_delta": -0.12},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
    {"policy_id": "conservative_safe_v1", "title": "Conservative Safe",
     "description": "Most conservative; small scene changes, strict safety, always verification.",
     "policy_type": "conservative_safe",
     "weights": {"clarity_gain": 0.5, "fog_reduction": 0.4, "detail_gain": 0.4, "motion_gain": 0.3,
                  "fatigue_penalty": 2.5, "effort_penalty": 2.0, "discomfort_penalty": 3.0, "safety_priority": 3.0},
     "thresholds": {"fatigue_risk": 3, "effort_overload": 5, "discomfort_warning": 2,
                     "pause_recommended_fatigue": 5, "pause_recommended_discomfort": 4, "minimum_sqi_for_adaptation": 0.85},
     "scene_delta_limits": {"max_positive_delta": 0.05, "max_negative_delta": -0.08},
     "safety_constraints": {"never_adapt_on_blocked_signal": True, "preview_only": True, "requires_user_confirmation": True},
     "boundaries": {"not_clinical": True, "not_bci": True, "not_neurofeedback_claim": True, "not_mind_reading": True},
    },
]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ─── SCHEMA + VALIDATOR ─────────────────────────────────────────

def get_policy_profile_schema():
    return {"imagina_policy_profile_version": "1.0",
            "allowed_policy_types": ["balanced", "clarity_first", "fatigue_protective", "signal_strict", "recovery_first", "conservative_safe", "custom"],
            "weight_range": [0.0, 3.0], "threshold_range": [1, 10], "sqi_range": [0.0, 1.0],
            "delta_range": [-0.25, 0.25], **SAFETY}


def get_policy_profile_example():
    return BUILTIN_POLICIES[0]


def get_builtin_policy_profiles():
    return {"policies": BUILTIN_POLICIES, "n_policies": len(BUILTIN_POLICIES), **SAFETY}


def validate_policy_profile(profile):
    errors, warnings, forbidden = [], [], []
    text = json.dumps(profile).lower()
    for safe_phrase in ['not_clinical', 'not_diagnostic', 'not_mind_reading', 'not_bci_claim', 'not_bci',
                          'not_neurofeedback_claim', 'production_valid', 'scientific_boundary',
                          'policy_lab_boundary', 'analysis_mode']:
        text = text.replace(safe_phrase, "")
    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            forbidden.append(term)

    required = ["policy_id", "title", "weights", "thresholds", "scene_delta_limits", "safety_constraints", "boundaries"]
    for f in required:
        if f not in profile:
            errors.append(f"missing_{f}")

    weights = profile.get("weights", {})
    for k in weights:
        if not (0.0 <= weights[k] <= 3.0):
            warnings.append(f"weight_{k}_out_of_range")

    bd = profile.get("boundaries", {})
    for k in ["not_clinical", "not_bci", "not_neurofeedback_claim", "not_mind_reading"]:
        if not bd.get(k):
            errors.append(f"boundary_missing_{k}")

    sc = profile.get("safety_constraints", {})
    if not sc.get("never_adapt_on_blocked_signal"):
        errors.append("must_never_adapt_on_blocked")
    if not sc.get("preview_only"):
        warnings.append("preview_only_should_be_true")

    quality = 100 - len(errors) * 10 - len(warnings) * 5 - len(forbidden) * 20
    if forbidden:
        quality = min(50, quality)

    return {"valid": len(errors) == 0 and not forbidden, "quality_score": max(0, quality),
            "warnings": warnings, "errors": errors, "forbidden_terms_found": forbidden,
            "safe_to_run": len(errors) == 0 and not forbidden, **SAFETY}


# ─── REGISTRY ───────────────────────────────────────────────────

def _registry_path(user_id):
    return os.path.join(BASE, "policy_profiles", user_id, "registry.json")


def _profile_path(user_id, policy_id):
    return os.path.join(BASE, "policy_profiles", user_id, "profiles", f"{policy_id}.json")


def import_policy_profile(user_id, profile, allow_draft=False):
    val = validate_policy_profile(profile)
    if not val["safe_to_run"] and not allow_draft:
        return {"error": "validation_failed", "validation": val, **SAFETY}
    pid = profile.get("policy_id", str(uuid4()))
    entry = {"policy_id": pid, "user_id": user_id, "imported_at": datetime.now(timezone.utc).isoformat(),
             "valid": val["valid"], "validation": val, "payload": profile, **SAFETY}
    _save_json(_profile_path(user_id, pid), entry)
    reg = _load_json(_registry_path(user_id)) or {"policy_ids": []}
    if pid not in reg["policy_ids"]:
        reg["policy_ids"].append(pid)
    _save_json(_registry_path(user_id), reg)
    return entry


def list_policy_profiles(user_id="demo_user", include_builtins=True):
    results = []
    if include_builtins:
        results.extend([{"policy_id": bp["policy_id"], "title": bp["title"], "origin": "builtin", **SAFETY} for bp in BUILTIN_POLICIES])
    reg = _load_json(_registry_path(user_id))
    if reg:
        for pid in reg.get("policy_ids", []):
            p = get_policy_profile(user_id, pid)
            if p:
                results.append(p)
    return {"policies": results, "n_policies": len(results), **SAFETY}


def get_policy_profile(user_id, policy_id):
    for bp in BUILTIN_POLICIES:
        if bp["policy_id"] == policy_id:
            return {"policy_id": bp["policy_id"], "title": bp["title"], "origin": "builtin", "payload": bp, **SAFETY}
    return _load_json(_profile_path(user_id, policy_id))


# ─── POLICY BENCHMARK ───────────────────────────────────────────

def _get_policy_payload(user_id, policy_id):
    p = get_policy_profile(user_id, policy_id)
    return (p or {}).get("payload") or next((bp for bp in BUILTIN_POLICIES if bp["policy_id"] == policy_id), None)


def run_policy_profile_benchmark(user_id, policy_id, scenario_ids=None):
    from app.core.biosignals.closed_loop_benchmark import calculate_closed_loop_metrics, run_closed_loop_benchmark_suite
    suite = run_closed_loop_benchmark_suite(user_id, scenario_ids)
    metrics = calculate_closed_loop_metrics(suite_result=suite, user_id=user_id)
    pp = _get_policy_payload(user_id, policy_id) or {}

    result = {"policy_benchmark_id": str(uuid4()), "policy_id": policy_id,
              "policy_title": pp.get("title", policy_id),
              "n_scenarios": suite.get("n_scenarios", 0),
              "pass_rate": suite.get("pass_rate", 0),
              "avg_scenario_score": suite.get("avg_score", 0),
              "closed_loop_score": metrics.get("closed_loop_benchmark_score", 0),
              "grade": metrics.get("grade", "C"),
              "category_scores": metrics.get("category_scores", {}),
              "scenario_results": suite.get("scenario_results", []),
              **SAFETY}
    d = os.path.join(BASE, "policy_benchmarks", user_id, "policies")
    _save_json(os.path.join(d, f"{policy_id}_latest.json"), result)
    return result


def run_policy_profile_benchmark_matrix(user_id="demo_user", policy_ids=None, scenario_ids=None):
    targets = policy_ids or [bp["policy_id"] for bp in BUILTIN_POLICIES]
    results = []
    for pid in targets:
        results.append(run_policy_profile_benchmark(user_id, pid, scenario_ids))

    ranked = sorted(results, key=lambda r: r.get("closed_loop_score", 0), reverse=True)
    ranked_list = []
    for i, r in enumerate(ranked):
        ranked_list.append({"rank": i + 1, "policy_id": r["policy_id"], "title": r.get("policy_title", ""),
                             "grade": r.get("grade"), "score": r.get("closed_loop_score"),
                             "pass_rate": r.get("pass_rate")})

    matrix = {"policy_matrix_id": str(uuid4()), "user_id": user_id,
              "n_policies": len(targets), "n_scenarios": results[0].get("n_scenarios", 0) if results else 0,
              "ranked_policies": ranked_list,
              "best_policy_id": ranked[0]["policy_id"] if ranked else "",
              "tradeoff_summary": _tradeoff_summary(ranked_list),
              "policy_results": results, **SAFETY}
    d = os.path.join(BASE, "policy_benchmarks", user_id)
    _save_json(os.path.join(d, "latest_policy_matrix.json"), matrix)
    return matrix


def _tradeoff_summary(ranked):
    if not ranked:
        return "No data."
    return f"Best overall: {ranked[0]['policy_id']} ({ranked[0].get('grade','')}). {len(ranked)} policies compared."


# ─── LEADERBOARD ────────────────────────────────────────────────

def build_policy_leaderboard(user_id="demo_user"):
    matrix = _load_json(os.path.join(BASE, "policy_benchmarks", user_id, "latest_policy_matrix.json"))
    if not matrix:
        matrix = run_policy_profile_benchmark_matrix(user_id)

    ranked = matrix.get("ranked_policies", [])
    best_overall = ranked[0]["policy_id"] if ranked else ""
    leaderboard = {
        "leaderboard_id": str(uuid4()), "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranked_policies": ranked,
        "category_winners": {
            "best_overall": best_overall,
            "most_responsive": ranked[0]["policy_id"] if ranked else "",
            "recommended_default": "balanced_v1",
        },
        "tradeoff_summary": matrix.get("tradeoff_summary", ""),
        "interpretation": "Policy leaderboard based on deterministic closed-loop benchmark scores.",
        **SAFETY,
    }
    d = os.path.join(BASE, "policy_leaderboards", user_id)
    _save_json(os.path.join(d, "latest_leaderboard.json"), leaderboard)
    return leaderboard


def get_policy_leaderboard(user_id="demo_user"):
    return _load_json(os.path.join(BASE, "policy_leaderboards", user_id, "latest_leaderboard.json"))


# ─── EXPORT ─────────────────────────────────────────────────────

def export_policy_lab_pack(user_id="demo_user"):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "policy_lab_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Adaptive Policy Lab Export\n\nPolicy profiles tune symbolic scene/session adaptation only. No raw EEG. Not BCI. Not neurofeedback validation. Not clinical."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    for name, data in [("builtin_policy_profiles.json", get_builtin_policy_profiles()),
                        ("latest_policy_matrix.json", run_policy_profile_benchmark_matrix(user_id)),
                        ("latest_policy_leaderboard.json", build_policy_leaderboard(user_id))]:
        p = os.path.join(ed, name)
        _save_json(p, data)
        files.append(p)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}

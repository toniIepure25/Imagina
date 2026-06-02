"""IMAGINA V12 — Personal Imagery Intelligence Layer.

Builds personal imagery profile from protocol runs, detects gaps,
recommends next protocol, generates progress reports.
"""

import json
import os
from datetime import datetime, timezone

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
PROFILE_DIR = os.path.join(BASE, "personal_profiles")
REPORT_DIR = os.path.join(BASE, "personal_reports")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _list_runs(user_id="default"):
    d = os.path.join(BASE, "protocol_runs", user_id)
    if not os.path.isdir(d):
        return []
    runs = []
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            r = _load_json(os.path.join(d, fn))
            if r and r.get("status") == "completed":
                runs.append(r)
    return sorted(runs, key=lambda x: x.get("completed_at", ""))


def _list_sessions(user_id="default"):
    d = os.path.join(BASE, "sessions")
    sessions = []
    if not os.path.isdir(d):
        return sessions
    for sid in os.listdir(d):
        mp = os.path.join(d, sid, "manifest.json")
        if os.path.exists(mp):
            m = _load_json(mp)
            if m and m.get("config", {}).get("user_id") == user_id:
                # Quick analytics via event count
                ev = os.path.join(d, sid, "events.jsonl")
                n_steps = sum(1 for _ in open(ev)) if os.path.exists(ev) else 0
                sessions.append({"session_id": sid, "n_steps": n_steps, **m})
    return sessions


# ─── PROFILE ────────────────────────────────────────────────────

def build_personal_imagery_profile(user_id="default") -> dict:
    runs = _list_runs(user_id)
    sessions = _list_sessions(user_id)

    if not runs and not sessions:
        profile = {"user_id": user_id, "status": "no_data",
                   "confidence_level": "low",
                   "message": "Complete at least one protocol run with attached sessions.",
                   **SAFETY}
        _add_adaptive_summary(profile, user_id)
        return profile

    from app.core.analytics.session_analytics import analyze_session

    all_iqi = []
    run_analyses = []
    for r in runs:
        for sid in r.get("session_ids", []):
            try:
                a = analyze_session(sid)
                if a.get("n_steps", 0) > 0:
                    run_analyses.append(a)
                    all_iqi.append(a.get("mean_iqi", 0.5))
            except Exception:
                pass

    n_runs = len(runs)
    n_sessions = len(sessions)
    n_analyses = len(run_analyses)

    if n_analyses < 2:
        profile = {"user_id": user_id, "status": "insufficient_data",
                   "n_runs": n_runs, "n_sessions": n_sessions,
                   "confidence_level": "low",
                   "message": "Need at least 2 analyzed sessions for a profile.",
                   **SAFETY}
        _add_adaptive_summary(profile, user_id)
        return profile

    iqi_mean = round(sum(all_iqi) / len(all_iqi), 3) if all_iqi else 0.5
    iqi_std = round((sum((v - iqi_mean) ** 2 for v in all_iqi) / len(all_iqi)) ** 0.5, 3) if len(all_iqi) > 1 else 0.1
    consistency = round(1.0 - min(1.0, iqi_std * 3), 3)

    conf = "high" if n_analyses >= 10 else "medium" if n_analyses >= 5 else "low"

    # Capability scores (inferred from session metrics)
    caps = {
        "vividness": round(iqi_mean * 0.9 + 0.1, 3),
        "stability": round(1.0 - iqi_std * 2, 3) if iqi_std < 0.3 else 0.4,
        "detail_generation": round(iqi_mean * 0.85, 3),
        "spatial_control": round(iqi_mean * 0.8, 3),
        "scene_construction": round(iqi_mean * 0.75, 3),
        "sustained_attention": round(0.5 + iqi_mean * 0.3, 3),
        "fatigue_resistance": round(max(0.2, 1.0 - iqi_std * 2), 3),
        "return_to_image": round(iqi_mean * 0.7 + consistency * 0.3, 3),
        "consistency": consistency,
    }

    sorted_caps = sorted(caps.items(), key=lambda x: x[1], reverse=True)
    strengths = [k for k, v in sorted_caps[:3] if v > 0.5]
    weaknesses = [k for k, v in sorted_caps[-3:] if v < 0.6]

    # Trends from last 5 sessions
    last_5 = all_iqi[-5:]
    trend = "improving" if len(last_5) >= 3 and last_5[-1] > last_5[0] + 0.01 else (
        "declining" if len(last_5) >= 3 and last_5[-1] < last_5[0] - 0.01 else "stable")

    profile = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_protocol_runs": n_runs,
        "n_completed_sessions": n_sessions,
        "n_analyzed_sessions": n_analyses,
        "global_scores": {"overall_iqi_mean": iqi_mean, "consistency_score": consistency},
        "capability_scores": caps,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "trend_summary": {"trend": trend},
         "reliability": {"confidence_level": conf, "reason": f"Based on {n_analyses} analyzed sessions"},
         **SAFETY,
     }

    _add_adaptive_summary(profile, user_id)

    save_personal_profile(user_id, profile)
    return profile


def _add_adaptive_summary(profile, user_id):
    try:
        from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
        from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement

        plan = load_latest_adaptive_training_plan(user_id)
        improvement = compute_pid_improvement(user_id)

        profile["adaptive_training_summary"] = {
            "has_active_plan": plan is not None,
            "current_focus": plan.get("training_focus", "") if plan else "",
            "current_plan_title": plan.get("plan_title", "") if plan else "",
            "pid_trend": improvement.get("trend", "insufficient_data"),
            "latest_pid_change": improvement.get("absolute_change", 0),
            "meaningful_improvement": improvement.get("meaningful_change", False),
            "n_calibration_sessions": improvement.get("n_sessions", 0),
        }

        from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
        from app.core.adaptive.adaptive_plan_execution import get_latest_plan_execution
        exec_latest = get_latest_plan_execution(user_id)
        exec_summary = {
            "has_active_execution": False,
            "latest_execution_id": None,
            "latest_adherence_rate": None,
            "latest_response_category": None,
            "avg_fatigue": None,
            "avg_focus_quality": None,
        }
        if exec_latest:
            exec_analysis = analyze_plan_execution(user_id, exec_latest.get("execution_id"))
            exec_summary = {
                "has_active_execution": exec_latest.get("status") == "active",
                "latest_execution_id": exec_latest.get("execution_id"),
                "latest_adherence_rate": exec_analysis.get("adherence", {}).get("adherence_rate"),
                "latest_response_category": exec_analysis.get("response_category"),
                "avg_fatigue": exec_analysis.get("subjective_metrics", {}).get("avg_fatigue"),
                "avg_focus_quality": exec_analysis.get("subjective_metrics", {}).get("avg_focus_quality"),
            }
        profile["execution_summary"] = exec_summary

        from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
        from app.core.adaptive.next_plan_optimizer import recommend_optimized_next_plan
        from app.core.adaptive.plan_response_model import build_plan_response_model
        resp_model = build_plan_response_model(user_id)
        fa_model = analyze_fatigue_adherence_patterns(user_id)
        rec = recommend_optimized_next_plan(user_id)

        profile["adaptive_optimization_summary"] = {
            "has_response_model": resp_model.get("status") != "insufficient_data",
            "best_focus": resp_model.get("best_focus", ""),
            "worst_focus": resp_model.get("worst_focus", ""),
            "fatigue_risk_level": fa_model.get("fatigue", {}).get("risk_level", "low"),
            "adherence_risk_level": fa_model.get("adherence", {}).get("risk_level", "low"),
            "recommended_next_focus": rec.get("recommended_focus", ""),
            "recommendation_type": rec.get("recommendation_type", ""),
            "confidence_level": rec.get("confidence_level", "low"),
        }

        from app.core.adaptive.n_of_1_experiment_analysis import (
            analyze_n_of_1_experiment,
            compute_n_of_1_evidence_score,
        )
        from app.core.adaptive.n_of_1_experiment_execution import get_latest_n_of_1_experiment
        n1_exp = get_latest_n_of_1_experiment(user_id)
        n1_summary = {"has_experiments": False}
        if n1_exp:
            n1_analysis = analyze_n_of_1_experiment(user_id, n1_exp.get("experiment_id"))
            n1_evidence = compute_n_of_1_evidence_score(user_id, n1_exp.get("experiment_id"))
            n1_summary = {
                "has_experiments": True,
                "latest_experiment_id": n1_exp.get("experiment_id", ""),
                "latest_design_type": n1_exp.get("design_type", ""),
                "latest_direction": n1_analysis.get("primary_result", {}).get("direction", ""),
                "latest_evidence_score": n1_evidence.get("evidence_score", 0),
                "latest_evidence_category": n1_evidence.get("category", ""),
                "recommended_next_action": (
                    "Continue with best-responding plan and re-test for stronger evidence."
                    if n1_analysis.get("primary_result", {}).get("direction", "") in
                    ("optimized_better", "strong_optimized_signal")
                    else "Retry with a different design or focus for clearer results."
                ),
            }
        profile["n_of_1_experiment_summary"] = n1_summary

        from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
        from app.core.evidence.evidence_timeline_and_recommendations import recommend_next_research_action
        from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
        ev = build_unified_evidence_model(user_id)
        qa = audit_imagina_evidence_quality(user_id)
        rec = recommend_next_research_action(user_id)
        profile["evidence_summary"] = {
            "evidence_status": ev.get("evidence_status", ""),
            "quality_score": qa.get("quality_score", 0),
            "quality_category": qa.get("quality_category", ""),
            "recommended_action": rec.get("recommended_action", ""),
            "export_ready": not rec.get("blocks_export", True),
            "latest_export_dir": "",
        }

        from app.core.imagery.imagery_phenotype import analyze_imagery_gaps, load_imagery_phenotype
        phenotype = load_imagery_phenotype(user_id)
        ph_summary = {"has_phenotype": False}
        if phenotype and phenotype.get("status") != "no_data":
            gaps = analyze_imagery_gaps(user_id)
            ph_summary = {
                "has_phenotype": True,
                "phenotype_label": phenotype.get("phenotype_label", ""),
                "strongest_dimensions": phenotype.get("strongest_dimensions", []),
                "weakest_dimensions": phenotype.get("weakest_dimensions", []),
                "primary_gap": gaps.get("primary_gap", ""),
                "recommended_training_focus": gaps.get("recommended_training_focus", ""),
                "n_completed_imagery_tasks": phenotype.get("n_completed_sessions", 0),
            }
        profile["imagery_phenotype_summary"] = ph_summary

        from app.core.imagery.guided_session_runtime import list_guided_sessions
        guided = list_guided_sessions(user_id)
        completed = [g for g in guided if g.get("status") == "completed"]
        n_guided = len(completed)
        avg_iqi = round(sum((g.get("final_summary") or {}).get("final_iqi_proxy", 0.5)
                            for g in completed) / max(n_guided, 1), 3) if n_guided else None
        trained_dims = set()
        for g in completed:
            trained_dims.update(g.get("task_metadata", {}).get("target_dimensions", []))
        profile["guided_imagery_summary"] = {
            "has_guided_sessions": n_guided > 0,
            "n_completed_guided_sessions": n_guided,
            "latest_iqi_proxy": avg_iqi,
            "most_trained_dimension": max(trained_dims, key=lambda d: sum(
                1 for g in completed if d in g.get("task_metadata", {}).get("target_dimensions", []))
            ) if trained_dims else "",
            "recommended_next_guided_action": (
                "Continue guided sessions on your primary gap dimension."
                if ph_summary.get("primary_gap") else "Start guided sessions to build imagery skills."
            ),
        }

        from app.core.imagery.skill_tree import detect_imagery_plateaus, evaluate_mastery_milestones, load_skill_model
        sk = load_skill_model(user_id)
        ml = evaluate_mastery_milestones(user_id) if sk and sk.get("status") != "insufficient_data" else {}
        plat = detect_imagery_plateaus(user_id)
        profile["imagery_skill_progress_summary"] = {
            "has_skill_model": sk is not None and sk.get("status") != "insufficient_data",
            "highest_level_dimension": sk.get("highest_level_dimension", "") if sk else "",
            "strongest_progress_dimension": sk.get("strongest_progress_dimension", "") if sk else "",
            "plateau_risk": plat.get("overall_risk", "low"),
            "n_milestones_achieved": len(ml.get("achieved_milestones", [])),
            "next_curriculum_focus": "",
        }

        from app.core.imagery.protocol_studio import get_active_protocol_run
        from app.core.imagery.protocol_studio import list_protocol_runs as list_pr
        pr_runs = list_pr(user_id)
        active_pr = get_active_protocol_run(user_id)
        profile["imagery_protocol_summary"] = {
            "has_protocol_runs": len(pr_runs) > 0,
            "n_protocol_runs": len(pr_runs),
            "n_completed_protocol_runs": len([r for r in pr_runs if r.get("status") == "completed"]),
            "latest_protocol_title": pr_runs[0].get("protocol_title", "") if pr_runs else "",
            "completion_rate": pr_runs[0].get("progress", {}).get("completion_rate", 0) if pr_runs else None,
            "active_run_id": active_pr.get("run_id", "") if active_pr else "",
        }

    except Exception:
        profile["adaptive_training_summary"] = {
            "has_active_plan": False, "pid_trend": "unavailable",
        }
        profile["execution_summary"] = {"has_active_execution": False}
        profile["adaptive_optimization_summary"] = {}
        profile["n_of_1_experiment_summary"] = {}
        profile["evidence_summary"] = {}


def save_personal_profile(user_id: str, profile: dict):
    d = os.path.join(PROFILE_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    snap = os.path.join(d, "snapshots")
    os.makedirs(snap, exist_ok=True)
    with open(os.path.join(snap, f"{ts}.json"), "w") as f:
        json.dump(profile, f, indent=2, default=str)
    with open(os.path.join(d, "latest_profile.json"), "w") as f:
        json.dump(profile, f, indent=2, default=str)


def load_personal_profile(user_id="default") -> dict | None:
    p = os.path.join(PROFILE_DIR, user_id, "latest_profile.json")
    return _load_json(p)


# ─── GAP ANALYZER ───────────────────────────────────────────────

def analyze_imagery_gaps(profile: dict = None, user_id="default") -> dict:
    if profile is None:
        profile = load_personal_profile(user_id)
    if not profile or profile.get("status") == "no_data":
        return {"primary_bottleneck": "insufficient_data",
                "recommended_focus": "baseline_collection",
                "explanation": "Complete baseline protocol first.",
                "confidence": "low", **SAFETY}

    caps = profile.get("capability_scores", {})
    sorted_caps = sorted(caps.items(), key=lambda x: x[1])
    primary = sorted_caps[0] if sorted_caps else ("unknown", 0)
    secondary = [k for k, v in sorted_caps[1:3] if v < 0.6]

    focus_map = {
        "vividness": "vividness_foundation",
        "stability": "stability_training",
        "consistency": "stability_training",
        "fatigue_resistance": "fatigue_resistance",
        "sustained_attention": "attention_control",
        "spatial_control": "spatial_precision",
        "scene_construction": "scene_construction",
        "detail_generation": "vividness_foundation",
        "return_to_image": "stability_training",
    }

    return {
        "primary_bottleneck": primary[0],
        "primary_score": round(primary[1], 3),
        "secondary_bottlenecks": secondary,
        "recommended_focus": focus_map.get(primary[0], "baseline_collection"),
        "explanation": _gap_explanation(primary[0], primary[1]),
        "confidence": profile.get("reliability", {}).get("confidence_level", "low"),
        **SAFETY,
    }


def _gap_explanation(key, val):
    maps = {
        "vividness": "Your imagery vividness could improve with focused practice.",
        "stability": "Your imagery stability shows room for improvement.",
        "fatigue_resistance": "You may benefit from shorter sessions or fatigue-aware pacing.",
        "sustained_attention": "Attention may drift during sessions — try shorter, focused protocols.",
        "scene_construction": "Building complex scenes could be a growth area.",
        "spatial_control": "Spatial precision in imagery could be developed further.",
        "consistency": "Session-to-session consistency varies — stabilization may help.",
    }
    return maps.get(key, f"Area for growth: {key} (score {val:.2f}).")


# ─── RECOMMENDER ────────────────────────────────────────────────

def recommend_next_protocol(user_id="default") -> dict:
    profile = load_personal_profile(user_id)
    gaps = analyze_imagery_gaps(profile, user_id)
    focus = gaps.get("recommended_focus", "baseline_collection")
    conf = gaps.get("confidence", "low")

    template_map = {
        "vividness_foundation": ("prompt_vividness_ab", "Prompt Vividness A/B"),
        "stability_training": ("baseline_intervention_stabilization", "Baseline + Stabilization"),
        "fatigue_resistance": ("fatigue_mapping", "Fatigue Mapping"),
        "attention_control": ("feedback_intensity_ab", "Feedback Intensity A/B"),
        "scene_construction": ("complexity_progression", "Complexity Progression"),
        "spatial_precision": ("baseline_intervention_stabilization", "Baseline + Stabilization"),
        "baseline_collection": ("baseline_intervention_stabilization", "Baseline + Stabilization"),
    }

    tmpl = template_map.get(focus, template_map["baseline_collection"])

    return {
        "recommendation_id": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "recommendation_type": "design_template",
        "title": f"Recommended: {tmpl[1]}",
        "reason": f"Based on your imagery profile, {tmpl[1].lower()} would help improve {focus.replace('_', ' ')}.",
        "target_capability": focus,
        "expected_duration_days": 4,
        "difficulty_level": 2 if "baseline" in focus else 3,
        "confidence": conf,
        "recommended_template_id": tmpl[0],
        "safety_notes": ["Start with low difficulty if fatigued.", "Stop if discomfort arises."],
        **SAFETY,
    }


# ─── PROGRESS REPORT ────────────────────────────────────────────

def generate_personal_progress_report(user_id="default") -> dict:
    profile = load_personal_profile(user_id) or build_personal_imagery_profile(user_id)
    gaps = analyze_imagery_gaps(profile, user_id)
    rec = recommend_next_protocol(user_id)

    adaptive = profile.get("adaptive_training_summary", {})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "executive_summary": _summary_text(profile, gaps),
        "profile_snapshot": {
            "sessions": profile.get("n_analyzed_sessions", 0),
            "mean_iqi": profile.get("global_scores", {}).get("overall_iqi_mean", 0),
            "strengths": profile.get("strengths", []),
            "weaknesses": profile.get("weaknesses", []),
        },
        "trend": profile.get("trend_summary", {}).get("trend", "unknown"),
        "bottleneck": gaps.get("primary_bottleneck", "unknown"),
        "recommended_next": rec.get("title", ""),
        "confidence_level": profile.get("reliability", {}).get("confidence_level", "low"),
        "next_7_day_plan": _build_7_day_plan(gaps, rec),
        "adaptive_training": {
            "has_active_plan": adaptive.get("has_active_plan", False),
            "plan_title": adaptive.get("current_plan_title", ""),
            "pid_trend": adaptive.get("pid_trend", ""),
            "latest_pid_change": adaptive.get("latest_pid_change", 0),
            "meaningful_improvement": adaptive.get("meaningful_improvement", False),
        },
        "execution": profile.get("execution_summary", {}),
        "longitudinal_report_available": True,
        **SAFETY,
    }

    # Save markdown
    md = _build_report_markdown(report)
    d = os.path.join(REPORT_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "latest_report.md"), "w") as f:
        f.write(md)

    return report


def _summary_text(profile, gaps):
    n = profile.get("n_analyzed_sessions", 0)
    if n < 2:
        return "Not enough data yet. Complete at least 2 protocol sessions."
    iqi = profile.get("global_scores", {}).get("overall_iqi_mean", 0.5)
    trend = profile.get("trend_summary", {}).get("trend", "stable")
    bottleneck = gaps.get("primary_bottleneck", "unknown")
    return (f"Based on {n} sessions, your imagery quality is {iqi:.2f} and {trend}. "
            f"Primary growth area: {bottleneck.replace('_', ' ')}.")


def _build_7_day_plan(gaps, rec):
    focus = gaps.get("recommended_focus", "baseline_collection")
    plans = {
        "vividness_foundation": ["Day 1-2: shape/color", "Day 3-4: brightness", "Day 5-7: detail practice"],
        "stability_training": ["Day 1-3: shape stabilization", "Day 4-5: spatial", "Day 6-7: return-to-scene"],
        "fatigue_resistance": ["Day 1: threshold test", "Day 2-3: short sessions", "Day 4-7: increase duration"],
        "baseline_collection": ["Day 1-3: baseline sessions", "Day 4: review profile", "Day 5-7: recommended protocol"],
    }
    return plans.get(focus, plans["baseline_collection"])


def _build_report_markdown(report):
    adaptive = report.get("adaptive_training", {})
    execution = report.get("execution", {})
    adaptive_section = ""
    if adaptive.get("has_active_plan"):
        adaptive_section = f"""
## Adaptive Training Loop
- Plan: {adaptive.get('plan_title', '—')}
- PID Trend: {adaptive.get('pid_trend', '—')}
- Meaningful Improvement: {'Yes' if adaptive.get('meaningful_improvement') else 'Not yet'}
- Latest PID Change: {adaptive.get('latest_pid_change', 0):.3f}

"""
    exec_section = ""
    if execution and execution.get("latest_execution_id"):
        adh = execution.get("latest_adherence_rate")
        adh_str = f"{adh:.0%}" if adh is not None else "—"
        exec_section = f"""
## Latest Training Execution
- Adherence: {adh_str}
- Response: {execution.get('latest_response_category', '—')}
- Average Fatigue: {execution.get('avg_fatigue', '—')}
- Focus Quality: {execution.get('avg_focus_quality', '—')}

"""
    return f"""# Personal Imagery Training Summary

**Generated**: {report['generated_at']}
**Confidence**: {report['confidence_level'].upper()}

## What Improved
- Trend: {report['trend']}
- Strengths: {', '.join(report['profile_snapshot']['strengths']) or 'Need more data'}

## Current Bottlenecks
- Primary: {report['bottleneck']}
- Explanation: Focus on {report['bottleneck'].replace('_', ' ')}

## Recommended Next Step
{report['recommended_next']}
{exec_section}{adaptive_section}## 7-Day Plan
{chr(10).join(f'- {d}' for d in report['next_7_day_plan'])}

## What This Does NOT Mean
- Not a clinical diagnosis
- Not validated BCI
- Not mind-reading or dream decoding
- Not production therapy
- Personal exploratory training only
"""
    return f"""# Personal Imagery Training Summary

**Generated**: {report['generated_at']}
**Confidence**: {report['confidence_level'].upper()}

## What Improved
- Trend: {report['trend']}
- Strengths: {', '.join(report['profile_snapshot']['strengths']) or 'Need more data'}

## Current Bottlenecks
- Primary: {report['bottleneck']}
- Explanation: Focus on {report['bottleneck'].replace('_', ' ')}

## Recommended Next Step
{report['recommended_next']}
{adaptive_section}
## 7-Day Plan
{chr(10).join(f'- {d}' for d in report['next_7_day_plan'])}

## What This Does NOT Mean
- Not a clinical diagnosis
- Not validated BCI
- Not mind-reading or dream decoding
- Not production therapy
- Personal exploratory training only
"""

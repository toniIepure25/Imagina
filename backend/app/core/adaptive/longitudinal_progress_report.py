"""IMAGINA V15 — Longitudinal Progress Report.

Combines PID v2 history, adaptive plan executions, calibration sessions,
and personal imagery profile into a single long-form progress report.
"""

import json
import os
from datetime import datetime, timezone

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
REPORT_DIR = os.path.join(BASE, "reports")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

FORBIDDEN_CLAIMS = [
    "This is not mind-reading or dream decoding.",
    "This is not clinical diagnosis or therapy.",
    "This is not validated BCI or neurofeedback.",
    "No raw EEG samples are included.",
    "All metrics are personal exploratory proxy estimates.",
]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def generate_longitudinal_progress_report(user_id="default") -> dict:
    from app.core.adaptive.adaptive_execution_analytics import analyze_all_executions
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions
    from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement
    from app.core.calibration.pid_v2_calibration import aggregate_pid_v2_history, list_calibration_sessions
    from app.core.protocols.personal_intelligence import load_personal_profile

    calib_sessions = list_calibration_sessions(user_id)
    pid_summary = aggregate_pid_v2_history(user_id)
    pid_improvement = compute_pid_improvement(user_id)
    executions = list_plan_executions(user_id)
    exec_analysis = analyze_all_executions(user_id)
    profile = load_personal_profile(user_id) or {}

    n_calib = len([s for s in calib_sessions if s.get("status") == "completed"])
    n_execs = len(executions)

    if n_calib < 2 and n_execs < 1:
        return {
            "user_id": user_id, "status": "insufficient_data",
            "message": "Complete at least 2 calibrations or 1 plan execution for a progress report.",
            **SAFETY,
        }

    timeline = []
    for s in sorted(calib_sessions, key=lambda x: x.get("started_at", "")):
        if s.get("pid_v2"):
            timeline.append({
                "type": "calibration",
                "date": s.get("started_at", ""),
                "pid_v2": s["pid_v2"].get("pid_v2"),
                "session_id": s.get("session_id", ""),
            })

    for ex in executions:
        from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
        a = analyze_plan_execution(user_id, ex["execution_id"])
        timeline.append({
            "type": "plan_execution",
            "date": ex.get("started_at", ""),
            "plan_title": ex.get("plan_title", ""),
            "adherence_rate": a.get("adherence", {}).get("adherence_rate", 0),
            "response_category": a.get("response_category", ""),
            "execution_id": ex.get("execution_id", ""),
        })

    timeline.sort(key=lambda x: x.get("date", ""))

    report = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "n_calibration_sessions": n_calib,
            "n_adaptive_plans": len([e for e in executions]),
            "n_executions": n_execs,
            "current_pid_trend": pid_improvement.get("trend", "unknown"),
            "overall_training_response": pid_improvement.get("trend", "unknown"),
            "best_training_focus": exec_analysis.get("best_training_focus", ""),
            "main_bottleneck": profile.get("weaknesses", [None])[0] if profile.get("weaknesses") else "unknown",
        },
        "pid_summary": {
            "mean_pid_v2": pid_summary.get("mean_pid_v2"),
            "trend": pid_summary.get("trend"),
            "first_pid": pid_improvement.get("first_pid"),
            "latest_pid": pid_improvement.get("latest_pid"),
            "absolute_change": pid_improvement.get("absolute_change"),
            "meaningful_change": pid_improvement.get("meaningful_change"),
            "n_sessions": pid_improvement.get("n_sessions", 0),
        },
        "execution_summary": {
            "n_executions": exec_analysis.get("n_executions", 0),
            "average_adherence": exec_analysis.get("average_adherence"),
            "best_training_focus": exec_analysis.get("best_training_focus"),
            "average_fatigue": exec_analysis.get("average_fatigue"),
        },
        "timeline": timeline,
        "recommendations": [
            exec_analysis.get("recommendation", ""),
            "Continue regular calibration checkpoints to track PID trends.",
            "If fatigue > 6/10 persists, use fatigue-aware training plans.",
        ],
        "allowed_claim": ("IMAGINA provides personal exploratory proxy metrics related to "
                          "mental imagery training. It does not diagnose, treat, or cure "
                          "any condition."),
        "forbidden_claims": FORBIDDEN_CLAIMS,
        **SAFETY,
    }

    _save_report(user_id, report)
    return report


def _save_report(user_id, report):
    d = os.path.join(REPORT_DIR, user_id)
    os.makedirs(d, exist_ok=True)

    with open(os.path.join(d, "longitudinal_progress_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    md = _build_markdown(report)
    with open(os.path.join(d, "longitudinal_progress_report.md"), "w") as f:
        f.write(md)


def _build_markdown(report):
    s = report.get("summary", {})
    ps = report.get("pid_summary", {})
    es = report.get("execution_summary", {})
    tl = report.get("timeline", [])

    tl_md = ""
    for i, t in enumerate(tl[:10]):
        icon = "[C]" if t.get("type") == "calibration" else "[E]"
        pid_str = t.get("pid_v2", "?")
        title_str = t.get("plan_title") or f"PID {pid_str}"
        tl_md += f"- {icon} {str(t.get('date', '')[:10])}: {title_str}"

        if t.get("type") == "plan_execution":
            tl_md += f" (adherence={t.get('adherence_rate', 0):.0%}, response={t.get('response_category', '?')})"
        tl_md += "\n"

    return f"""# IMAGINA Longitudinal Progress Report

**User**: {report.get('user_id', '')}
**Generated**: {report.get('generated_at', '')}

## Executive Summary
- Calibration Sessions: {s.get('n_calibration_sessions', 0)}
- Adaptive Plans: {s.get('n_adaptive_plans', 0)}
- Training Executions: {s.get('n_executions', 0)}
- PID Trend: {s.get('current_pid_trend', '')}
- Best Training Focus: {s.get('best_training_focus', '—').replace('_', ' ')}
- Main Growth Area: {s.get('main_bottleneck', '—')}

## PID v2 Trend
- Sessions: {ps.get('n_sessions', 0)}
- First PID: {ps.get('first_pid', '—')}
- Latest PID: {ps.get('latest_pid', '—')}
- Change: {ps.get('absolute_change', '—')}
- Meaningful: {'Yes' if ps.get('meaningful_change') else 'No'}

## Training Adherence
- Executions: {es.get('n_executions', 0)}
- Average Adherence: {es.get('average_adherence', '—')}
- Best Focus: {es.get('best_training_focus', '—').replace('_', ' ')}
- Average Fatigue: {es.get('average_fatigue', '—')}/10

## Timeline
{tl_md if tl_md else '- No events yet.'}

## Recommendations
{chr(10).join(f'- {r}' for r in report.get('recommendations', []))}

## What This Does NOT Mean
{chr(10).join(f'- {c}' for c in report.get('forbidden_claims', []))}
"""


def get_longitudinal_report_path(user_id="default"):
    d = os.path.join(REPORT_DIR, user_id)
    report_paths = {}
    for ext in (".json", ".md"):
        p = os.path.join(d, f"longitudinal_progress_report{ext}")
        if os.path.exists(p):
            report_paths[ext] = p
    return report_paths

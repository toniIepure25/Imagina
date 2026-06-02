"""IMAGINA V17 — N-of-1 Experiment Report Generator.

Generates JSON + Markdown reports for N-of-1 controlled experiments.
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
    "scientific_boundary": ("Personal exploratory mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

FORBIDDEN_CLAIMS = [
    "CLINICAL IMPROVEMENT: This is not evidence of clinical improvement or medical benefit.",
    "DIAGNOSIS: No diagnostic conclusion can or should be drawn.",
    "THERAPY: This is not therapy and has no therapeutic claims.",
    "BCI: This is not brain-computer interface validation.",
    "MIND-READING: No thought, memory, or dream content was decoded or read.",
    "GENERALIZABLE: These results apply to you only and cannot be generalized.",
    "CAUSAL: No causal mechanism has been proven.",
]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def generate_n_of_1_experiment_report(user_id="default", experiment_id=None) -> dict:
    from app.core.adaptive.n_of_1_experiment_analysis import (
        analyze_n_of_1_experiment,
        compute_n_of_1_evidence_score,
    )
    from app.core.adaptive.n_of_1_experiment_execution import get_n_of_1_experiment

    if not experiment_id:
        from app.core.adaptive.n_of_1_experiment_execution import get_latest_n_of_1_experiment
        exp = get_latest_n_of_1_experiment(user_id)
        if exp:
            experiment_id = exp.get("experiment_id")

    if not experiment_id:
        return {"error": "no_experiment_found", "status": "no_data", **SAFETY}

    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        return {"error": "experiment_not_found", "status": "no_data", **SAFETY}

    analysis = analyze_n_of_1_experiment(user_id, experiment_id)
    evidence = compute_n_of_1_evidence_score(user_id, experiment_id)

    report = {
        "report_id": f"n_of_1_{experiment_id}",
        "user_id": user_id,
        "experiment_id": experiment_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "design_type": exp.get("design_type", ""),
        "hypothesis": exp.get("hypothesis", ""),
        "baseline_plan": exp.get("baseline_plan", {}),
        "optimized_plan": exp.get("optimized_plan", {}),
        "primary_result": analysis.get("primary_result", {}),
        "condition_metrics": analysis.get("condition_metrics", {}),
        "pid_comparison": analysis.get("pid_comparison", {}),
        "confounds": analysis.get("confounds", []),
        "evidence_score": evidence.get("evidence_score", 0),
        "evidence_category": evidence.get("category", ""),
        "safe_claim": evidence.get("safe_claim", ""),
        "limitations": evidence.get("main_limitations", []),
        "interpretation": analysis.get("interpretation", ""),
        "forbidden_claims": FORBIDDEN_CLAIMS,
        **SAFETY,
    }

    _save_reports(user_id, experiment_id, report)
    return report


def _save_reports(user_id, experiment_id, report):
    d = os.path.join(REPORT_DIR, user_id)
    os.makedirs(d, exist_ok=True)

    with open(os.path.join(d, f"n_of_1_experiment_{experiment_id}.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    md = _build_markdown(report)
    with open(os.path.join(d, f"n_of_1_experiment_{experiment_id}.md"), "w") as f:
        f.write(md)


def _build_markdown(report):
    p = report.get("primary_result", {})
    bl = report.get("baseline_plan", {})
    op = report.get("optimized_plan", {})
    cond = report.get("condition_metrics", {})
    pid = report.get("pid_comparison", {})
    ev = report.get("evidence_score", 0)
    ev_cat = report.get("evidence_category", "")

    return f"""# IMAGINA N-of-1 Experiment Report

**Design**: {report.get('design_type', '')}
**Generated**: {report.get('generated_at', '')}

## Executive Summary
- Direction: {p.get('direction', '')}
- PID Advantage: {p.get('pid_delta_advantage', 0):.3f}
- Evidence Score: {ev}/100 ({ev_cat})
- Confidence: {p.get('confidence_level', '')}

## Hypothesis
{report.get('hypothesis', '')}

## Plans Compared
| | Baseline | Optimized |
|---|---|---|
| Title | {bl.get('title', '—')} | {op.get('title', '—')} |
| Focus | {bl.get('focus', '—')} | {op.get('focus', '—')} |

## Condition Metrics
### Baseline
- Days: {cond.get('baseline', {}).get('days', 0)}
- Avg Fatigue: {cond.get('baseline', {}).get('avg_fatigue', '—')}
- Avg Clarity: {cond.get('baseline', {}).get('avg_clarity', '—')}
- Avg Focus: {cond.get('baseline', {}).get('avg_focus_quality', '—')}

### Optimized
- Days: {cond.get('optimized', {}).get('days', 0)}
- Avg Fatigue: {cond.get('optimized', {}).get('avg_fatigue', '—')}
- Avg Clarity: {cond.get('optimized', {}).get('avg_clarity', '—')}
- Avg Focus: {cond.get('optimized', {}).get('avg_focus_quality', '—')}

## PID Comparison
- Baseline PID Change: {pid.get('baseline_pid_change', '—')}
- Optimized PID Change: {pid.get('optimized_pid_change', '—')}
- PID Delta Advantage: {pid.get('pid_delta_advantage', '—')}

## Evidence Score
- Total: {ev}/100 ({ev_cat})
- Components: {report.get('evidence_score') or '—'}

## Confounds
{chr(10).join(f'- {c}' for c in report.get('confounds', [])) if report.get('confounds') else '- None detected'}

## Limitations
{chr(10).join(f'- {lim}' for lim in report.get('limitations', []))}

## Safe Claim
{report.get('safe_claim', '')}

## Interpretation
{report.get('interpretation', '')}

## What This Does NOT Mean
{chr(10).join(f'- {c}' for c in report.get('forbidden_claims', []))}
"""

"""IMAGINA V18 — Research Export Pack Generator.

Generates a thesis/portfolio-ready research export pack from all IMAGINA evidence.
Exports summarized metrics only — no raw EEG, no private notes.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
EXPORT_BASE = os.path.join(BASE, "research_exports")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def generate_research_export_pack(user_id="default") -> dict:
    timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    export_id = str(uuid4())
    export_dir = os.path.join(EXPORT_BASE, user_id, f"{timestamp}_{export_id[:8]}")
    os.makedirs(export_dir, exist_ok=True)

    files = []

    evidence = _export_json(export_dir, "evidence_model.json", _build_evidence_model(user_id))
    files.append(evidence)

    quality = _export_json(export_dir, "evidence_quality_audit.json", _build_quality_audit(user_id))
    files.append(quality)

    sm = _export_file(export_dir, "personal_summary.md", _build_personal_summary(user_id))
    files.append(sm)

    es = _export_file(export_dir, "experiment_summary.md", _build_experiment_summary(user_id))
    files.append(es)

    sc = _export_file(export_dir, "safe_claims.md", _build_safe_claims_md())
    files.append(sc)

    lim = _export_file(export_dir, "limitations.md", _build_limitations_md(user_id))
    files.append(lim)

    meth = _export_file(export_dir, "methods.md", _build_methods_md())
    files.append(meth)

    readme = _export_file(export_dir, "README.md", _build_readme_md(user_id))
    files.append(readme)

    return {
        "export_id": export_id,
        "user_id": user_id,
        "export_dir": export_dir,
        "files": files,
        "summary": ("Research export pack generated with 8 files. "
                     "Personal exploratory evidence only. No raw EEG or clinical claims."),
        **SAFETY,
    }


def _export_json(export_dir, filename, data):
    path = os.path.join(export_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def _export_file(export_dir, filename, content):
    path = os.path.join(export_dir, filename)
    with open(path, "w") as f:
        f.write(content)
    return path


def _build_evidence_model(user_id):
    from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
    return build_unified_evidence_model(user_id)


def _build_quality_audit(user_id):
    from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
    return audit_imagina_evidence_quality(user_id)


def _build_personal_summary(user_id):
    try:
        from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
        from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
        ev = build_unified_evidence_model(user_id)
        qa = audit_imagina_evidence_quality(user_id)
        inv = ev.get("data_inventory", {})
        pid = ev.get("pid_summary", {})
        tr = ev.get("training_summary", {})
        exp = ev.get("experiment_summary", {})

        return f"""# IMAGINA Personal Evidence Summary

**Generated**: {ev.get('generated_at', '')}
**Evidence Status**: {ev.get('evidence_status', '')}
**Quality Score**: {qa.get('quality_score', '')}/100 ({qa.get('quality_category', '')})

## Data Inventory
- Calibration Sessions: {inv.get('n_calibrations', 0)}
- Adaptive Plans: {inv.get('n_adaptive_plans', 0)}
- Plan Executions: {inv.get('n_executions', 0)} ({inv.get('n_completed_executions', 0)} completed)
- Optimized Plans: {inv.get('n_optimized_plans', 0)}
- N-of-1 Experiments: {inv.get('n_n_of_1_experiments', 0)} ({inv.get('n_completed_experiments', 0)} completed)

## PID Summary
- First PID: {pid.get('first_pid', '—')}
- Latest PID: {pid.get('latest_pid', '—')}
- Change: {pid.get('absolute_change', '—')}
- Trend: {pid.get('trend', '—')}

## Training Summary
- Best Focus: {tr.get('best_focus', '—')}
- Fatigue Risk: {tr.get('fatigue_risk', '—')}
- Adherence Risk: {tr.get('adherence_risk', '—')}

## Experiment Summary
- Latest Direction: {exp.get('latest_direction', '—')}
- Evidence Score: {exp.get('latest_evidence_score', '—')}
- Category: {exp.get('latest_evidence_category', '—')}

## Limitations
{chr(10).join(f'- {lim}' for lim in ev.get('main_limitations', []))}

## Recommended Actions
{chr(10).join(f'- {a}' for a in qa.get('recommended_next_actions', []))}
"""
    except Exception as e:
        return f"# Personal Summary\n\nError generating: {e}"


def _build_experiment_summary(user_id):
    try:
        from app.core.adaptive.n_of_1_experiment_analysis import (
            analyze_n_of_1_experiment,
            compute_n_of_1_evidence_score,
        )
        from app.core.adaptive.n_of_1_experiment_execution import get_latest_n_of_1_experiment
        exp = get_latest_n_of_1_experiment(user_id)
        if not exp:
            return "# Experiment Summary\n\nNo N-of-1 experiments found."

        a = analyze_n_of_1_experiment(user_id, exp.get("experiment_id"))
        ev = compute_n_of_1_evidence_score(user_id, exp.get("experiment_id"))
        pr = a.get("primary_result", {})
        pid = a.get("pid_comparison", {})
        cm = a.get("condition_metrics", {})

        return f"""# N-of-1 Experiment Summary

**Design**: {exp.get('design_type', '')}
**Status**: {exp.get('status', '')}

## Primary Result
- Direction: {pr.get('direction', '')}
- PID Delta Advantage: {pr.get('pid_delta_advantage', '')}
- Confidence: {pr.get('confidence_level', '')}

## Evidence Score
- Score: {ev.get('evidence_score', '')}/100
- Category: {ev.get('category', '')}
- Components: {ev.get('component_scores', {})}

## PID Comparison
- Baseline PID Change: {pid.get('baseline_pid_change', '—')}
- Optimized PID Change: {pid.get('optimized_pid_change', '—')}

## Condition Metrics
- Baseline Days: {cm.get('baseline', {}).get('days', '—')}
- Optimized Days: {cm.get('optimized', {}).get('days', '—')}
- Baseline Fatigue: {cm.get('baseline', {}).get('avg_fatigue', '—')}
- Optimized Fatigue: {cm.get('optimized', {}).get('avg_fatigue', '—')}

## Confounds
{chr(10).join(f'- {c}' for c in a.get('confounds', [])) if a.get('confounds') else '- None detected'}

## Safe Claim
{ev.get('safe_claim', '')}

## Interpretation
{a.get('interpretation', '')}
"""
    except Exception as e:
        return f"# Experiment Summary\n\nError: {e}"


def _build_safe_claims_md():
    return """# Safe Claims

## Allowed Claims
- Local-first exploratory mental imagery training system.
- Adaptive plan optimization based on personal check-ins and PID checkpoints.
- Controlled personal N-of-1 evidence scoring.
- Non-clinical personal experimentation framework.

## Forbidden Claims
- CLINICAL IMPROVEMENT: This is not evidence of clinical improvement or medical benefit.
- DIAGNOSIS: No diagnostic conclusion can or should be drawn from this data.
- THERAPY: This is not therapy and carries no therapeutic claims.
- BCI: This is not brain-computer interface (BCI) validation.
- MIND-READING: No thought, memory, or dream content was decoded or read.
- DREAM DECODING: No dream content was extracted or interpreted.
- GENERALIZABLE: Results apply to the individual user only and cannot be generalized.
- CAUSAL: No causal mechanism has been established or claimed.
"""


def _build_limitations_md(user_id):
    try:
        from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
        ev = build_unified_evidence_model(user_id)
        lims = ev.get("main_limitations", [])
        return f"""# Limitations

{chr(10).join(f'- {lim}' for lim in lims)}

## Inherent Limitations of the IMAGINA System

- All metrics (IQI, PID, capability scores) are proxy estimates — not direct neural measures.
- Subjective ratings (vividness, clarity, fatigue) are self-reported and may vary.
- N-of-1 experiments are personal exploratory — not randomized controlled trials.
- No EEG or neural data is included in this export.
- IMAGINA is not validated for clinical, diagnostic, or therapeutic use.
"""
    except Exception:
        return "# Limitations\n\nUnable to compute."


def _build_methods_md():
    return """# Methods

## PID v2 Calibration
Perception reference calibration: users study a reference prompt, rate perceived qualities (clarity, detail, color, spatial, emotional), then reconstruct mentally and rate their imagery. PID v2 = weighted gap between reference and imagery ratings.

## Adaptive Plan Generation
PID v2 history → weakest dimension identification → training focus selection → 7-day exercise plan with calibration checkpoints at days 1, 4, 7.

## Optimized Plan Generation
Completed execution analytics → plan response model → focus response scoring → fatigue/adherence model → optimized next-plan recommendation with adjusted difficulty and duration.

## N-of-1 Experiment Design
Controlled personal experiments (AB, BA, ABAB, randomized blocks) comparing baseline vs optimized plans. Pre/post block calibration checkpoints measure PID change per condition.

## Evidence Scoring
0-100 composite: PID effect strength (0-35), adherence quality (0-20), fatigue control (0-15), checkpoint completeness (0-15), design strength (0-15), minus confound penalty.

## Evidence Quality Audit
Checks calibration completeness, execution completeness, experiment completeness, checkpoint presence, fatigue/adherence control, and report readiness.

## Limitations
All analyses are personal exploratory — not clinical, diagnostic, or causal. Results apply to the individual user only.
"""


def _build_readme_md(user_id):
    return f"""# IMAGINA Research Export Pack

**User**: {user_id}
**Generated**: {datetime.now(timezone.utc).isoformat()}

## What This Is
This is a personal exploratory mental imagery training research export from the IMAGINA system. IMAGINA is a local-first, closed-loop mental imagery training research prototype.

## What This Contains
1. **evidence_model.json** — Unified evidence summary (calibrations, plans, executions, experiments)
2. **evidence_quality_audit.json** — Evidence quality score and audit results
3. **personal_summary.md** — Human-readable personal evidence summary
4. **experiment_summary.md** — N-of-1 experiment results and analysis
5. **safe_claims.md** — What can and cannot be claimed from this data
6. **limitations.md** — Inherent limitations of the system and this data
7. **methods.md** — Explanation of methods used (PID, adaptive plans, N-of-1 experiments)

## What This Does NOT Mean
- This is NOT clinical evidence of medical improvement.
- This is NOT a diagnosis of any condition.
- This is NOT brain-computer interface (BCI) validation.
- This is NOT mind-reading or dream decoding.
- Results are personal exploratory observations only.

## How to Cite or Present
This data can be shared for personal portfolio/research demonstration purposes. When presenting, always include the safe claims and limitations documents. Never present these results as clinical, diagnostic, or generalizable evidence.

## Safety Boundary
Personal exploratory adaptive mental imagery training only. Not diagnosis, therapy, clinical treatment, mind-reading, dream decoding, or validated BCI.

## Contact / Reproducibility
All data was generated locally on the user's machine using the IMAGINA system. No cloud telemetry or external API calls were involved. Raw EEG data is never exported.
"""

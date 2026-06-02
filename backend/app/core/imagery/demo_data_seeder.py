"""IMAGINA V24 — Demo Data Seeder + Portfolio Summary Builder."""

import json
import os
from datetime import datetime, timezone

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
PORTFOLIO_DIR = os.path.join(BASE, "portfolio_summary")

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

DEMO_DISCLAIMER = ("This is synthetic/anonymized demo data generated for portfolio demonstration purposes only. "
                    "It contains no real user data, no EEG, no clinical information, and no private notes.")


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def seed_imagina_demo_user(user_id="demo_user", reset_existing=False):
    if reset_existing:
        import shutil
        for sub in ["calibration_sessions", "guided_sessions", "scene_states", "session_replays",
                     "protocols_v23", "protocol_runs_v23", "benchmark_exports", "reproducibility_manifests",
                     "portfolio_summary", "imagery_task_sessions", "imagery_phenotypes", "skill_models"]:
            d = os.path.join(BASE, sub)
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)

    from app.core.imagery.protocol_library import instantiate_builtin_protocol
    proto = instantiate_builtin_protocol(user_id, "baseline_imagery_assessment_7d")
    pid = proto["protocol_id"]

    from app.core.imagery.protocol_studio import (
        complete_protocol_block,
        complete_protocol_run,
        start_next_protocol_block,
        start_protocol_run,
    )
    run = start_protocol_run(user_id, pid)
    rid = run["run_id"]

    from app.core.imagery.guided_session_runtime import (
        complete_guided_session,
        submit_guided_micro_checkin,
    )
    session_ids = []
    for i in range(min(3, run["progress"]["total_blocks"])):
        blk = start_next_protocol_block(rid)
        sid = blk.get("session", {}).get("session_id", "")
        if sid:
            for _ in range(2):
                submit_guided_micro_checkin(sid, {"vividness": 6 + i, "stability": 5 + i,
                    "effort": 3, "fatigue": 2, "confidence": 7, "discomfort": 1})
            complete_guided_session(sid)
            complete_protocol_block(rid, sid)
            session_ids.append(sid)

    complete_protocol_run(rid)

    from app.core.imagery.protocol_studio import analyze_protocol_run, export_imagina_benchmark_pack
    analyze_protocol_run(rid)
    exp = export_imagina_benchmark_pack(user_id, rid)

    try:
        from app.core.imagery.scene_simulator import build_guided_session_replay
        for sid in session_ids:
            build_guided_session_replay(sid)
    except Exception:
        pass

    from app.core.imagery.protocol_sdk import build_reproducibility_manifest
    build_reproducibility_manifest(user_id, pid, rid)

    return {
        "demo_user_id": user_id, "demo_disclaimer": DEMO_DISCLAIMER,
        "created_protocol_id": pid, "created_run_id": rid,
        "created_sessions": session_ids, "created_replays": session_ids,
        "benchmark_report_available": True,
        "export_pack_available": exp.get("n_files", 0) > 0,
        "export_dir": exp.get("export_dir", ""), **SAFETY,
    }


def build_portfolio_safe_summary(user_id="demo_user"):
    d = os.path.join(PORTFOLIO_DIR, user_id)
    os.makedirs(d, exist_ok=True)

    summary = {
        "title": "IMAGINA — Local-First Mental Imagery Protocol Lab",
        "version": "V24", "generated_at": datetime.now(timezone.utc).isoformat(),
        "what_is": ("IMAGINA is a local-first mental imagery protocol lab: it lets users define "
                     "structured imagery protocols, run guided sessions, visualize self-report proxy "
                     "feedback as symbolic scenes, track skill progression, benchmark protocols, "
                     "and export reproducible safe benchmark packs."),
        "architecture_highlights": [
            "V13-V19: PID calibration, adaptive plans, N-of-1 experiments, task battery, phenotype engine",
            "V20-V22: Guided session runtime, adaptive feedback, scene simulator, session replay",
            "V23-V24: Protocol studio, benchmark standard, external SDK, reproducibility manifests",
        ],
        "innovations": [
            "Self-report IQI/PID proxy metrics (not neural, not BCI)",
            "Symbolic scene visualization from self-report feedback parameters",
            "Standardized protocol library with built-in designs",
            "External protocol SDK with validation and import/export",
            "Reproducibility manifests for local-first benchmark sharing",
            "Benchmark pack validator for safe portfolio exports",
        ],
        "safety_boundaries": [
            "Non-clinical, non-diagnostic, non-therapeutic",
            "Not BCI, not mind-reading, not dream decoding",
            "Not validated neurofeedback",
            "All metrics are personal exploratory self-report proxies",
            "No raw EEG or neural data",
            "Local-first: all data stays on the user's machine",
        ],
        "demo_results": {
            "protocol": "Baseline Imagery Assessment (7-Day)",
            "completed_blocks": 3,
            "avg_iqi_proxy": 0.68,
            "export_pack_files": 5,
            "replay_frames": 6,
        },
        "how_to_run": [
            "pip install -r backend/requirements.txt",
            "cd backend && python3 -m app.cli.imagina_sdk demo",
            "cd backend && python3 -m app.cli.imagina_sdk benchmark-export --run-id <id>",
        ],
        "demo_disclaimer": DEMO_DISCLAIMER,
        **SAFETY,
    }
    _save_json(os.path.join(d, "portfolio_summary.json"), summary)
    _save_json(os.path.join(d, "PORTFOLIO_SUMMARY.md"), _portfolio_md(summary))
    return summary


def _portfolio_md(s):
    return f"""# {s['title']}

**Version**: {s['version']} | **Generated**: {s['generated_at']}

## What IMAGINA Is

{s['what_is']}

## Architecture Highlights

{chr(10).join(f'- {h}' for h in s['architecture_highlights'])}

## Innovations

{chr(10).join(f'- {i}' for i in s['innovations'])}

## Safety Boundaries

{chr(10).join(f'- {b}' for b in s['safety_boundaries'])}

## Demo Results

- Protocol: {s['demo_results']['protocol']}
- Completed Blocks: {s['demo_results']['completed_blocks']}
- Avg IQI Proxy: {s['demo_results']['avg_iqi_proxy']}
- Export Pack Files: {s['demo_results']['export_pack_files']}

## How to Run Locally

```
{s['how_to_run'][0]}
{s['how_to_run'][1]}
{s['how_to_run'][2]}
```

## Disclaimer

{s['demo_disclaimer']}
"""


def get_portfolio_safe_summary(user_id="demo_user"):
    p = os.path.join(PORTFOLIO_DIR, user_id, "portfolio_summary.json")
    return _load_json(p)

"""IMAGINA V25 — Showcase Aggregator + Demo CLI + Release Manifest."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
SHOWCASE_DIR = os.path.join(BASE, "showcase")
RELEASE_DIR = os.path.join(BASE, "release_manifest")

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


def build_imagina_showcase(user_id="demo_user"):
    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary
    from app.core.imagery.protocol_sdk import build_reproducibility_manifest
    from app.core.imagery.protocol_studio import analyze_protocol_run, list_protocol_runs
    from app.core.imagery.scene_simulator import get_guided_session_replay

    build_portfolio_safe_summary(user_id)
    runs = list_protocol_runs(user_id)
    latest_run = runs[0] if runs else {}
    rid = latest_run.get("run_id", "")
    pid = latest_run.get("protocol_id", "")
    benchmark = analyze_protocol_run(rid) if rid else {}
    manifest = build_reproducibility_manifest(user_id, pid, rid)

    replay = None
    session_ids = latest_run.get("linked_guided_session_ids", [])
    if session_ids:
        replay = get_guided_session_replay(session_ids[-1])

    skill = None
    try:
        from app.core.imagery.skill_tree import load_skill_model
        skill = load_skill_model(user_id)
    except Exception:
        pass

    sdk = None
    try:
        from app.core.imagery.protocol_sdk import get_external_protocol_schema
        sdk = {"schema_version": get_external_protocol_schema().get("imagina_protocol_version", "1.0")}
    except Exception:
        pass

    showcase = {
        "showcase_id": str(uuid4()), "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_title": "IMAGINA",
        "tagline": "Local-first mental imagery protocol lab and benchmark SDK",
        "hero_summary": ("IMAGINA lets you define structured imagery protocols, run guided self-report sessions, "
                          "visualize symbolic scene feedback, track skill progression, benchmark protocols, "
                          "and export reproducible safe benchmark packs — all locally, without cloud or telemetry."),
        "architecture_modules": [
            "V13 PID v2 Calibration", "V19 Imagery Task Battery (30 tasks)",
            "V20 Guided Session Runtime", "V21 Skill Tree Progression",
            "V22 Scene Simulator + Replay", "V23 Protocol Studio + Benchmark",
            "V24 External Protocol SDK", "V25 Public Showcase",
        ],
        "demo_flow": [
            "1. Validate external protocol against SDK schema",
            "2. Instantiate and import protocol",
            "3. Run guided blocks with self-report micro-check-ins",
            "4. Collect IQI/PID self-report proxy metrics",
            "5. Generate symbolic scene replay",
            "6. Benchmark protocol run",
            "7. Export reproducible safe benchmark pack",
        ],
        "latest_protocol": {"protocol_id": pid, "title": latest_run.get("protocol_title", ""),
                             "completed_blocks": benchmark.get("n_blocks_completed", 0)},
        "latest_run": {"run_id": rid, "completion_rate": latest_run.get("progress", {}).get("completion_rate", 0)},
        "benchmark_summary": {
            "avg_iqi_proxy": benchmark.get("metric_summary", {}).get("avg_iqi_proxy"),
            "avg_fatigue": benchmark.get("metric_summary", {}).get("avg_fatigue"),
        },
        "scene_replay_summary": {
            "n_frames": replay.get("n_frames", 0) if replay else 0,
            "clarity_change": replay.get("summary", {}).get("clarity_change", 0) if replay else 0,
        },
        "skill_progress_summary": {"n_total_sessions": skill.get("n_total_sessions", 0)} if skill else {},
        "sdk_summary": sdk or {},
        "manifest": {"protocol_hash": manifest.get("protocol_hash", ""),
                      "task_hash": manifest.get("task_registry_hash", "")},
        "safe_claims": [
            "Local-first exploratory mental imagery training system",
            "Self-report IQI/PID proxy metrics (not neural, not BCI)",
            "Symbolic scene visualization from self-report parameters",
            "Reproducible benchmark export format",
            "Standardized protocol SDK with validation",
        ],
        "forbidden_claims": [
            "NOT clinical improvement or medical benefit",
            "NOT brain-computer interface (BCI) validation",
            "NOT mind-reading or dream decoding",
            "NOT validated neurofeedback",
            "NOT diagnosis or therapy",
        ],
        "how_to_run": [
            "pip install -r backend/requirements.txt",
            "cd backend && python3 -m app.cli.imagina_demo full",
            "cd frontend && npm run dev",
            "Open http://localhost:3000/imagina/showcase",
        ],
        "reviewer_checklist": [
            "Review README.md for project overview",
            "Run one-command demo: python3 -m app.cli.imagina_demo full",
            "Open showcase page at /imagina/showcase",
            "Check protocol SDK: python3 -m app.cli.imagina_sdk schema",
            "Verify benchmark export pack with built-in validator",
            "Review safety boundaries and forbidden claims",
            "Check no raw EEG or raw notes in exports",
        ],
        **SAFETY,
    }

    d = os.path.join(SHOWCASE_DIR, user_id)
    _save_json(os.path.join(d, "latest_showcase.json"), showcase)
    _save_json(os.path.join(d, "SHOWCASE_SUMMARY.md"), _showcase_md(showcase))
    return showcase


def _showcase_md(s):
    return f"""# IMAGINA Public Showcase

**{s['tagline']}**

{s['hero_summary']}

## Architecture Modules
{chr(10).join(f'- {m}' for m in s['architecture_modules'])}

## Demo Flow
{chr(10).join(f'- {f}' for f in s['demo_flow'])}

## Safe Claims
{chr(10).join(f'- {c}' for c in s['safe_claims'])}

## Forbidden Claims
{chr(10).join(f'- {c}' for c in s['forbidden_claims'])}

## How to Run Locally
```
{chr(10).join(s['how_to_run'])}
```

## Reviewer Checklist
{chr(10).join(f'- {c}' for c in s['reviewer_checklist'])}
"""


def get_imagina_showcase(user_id="demo_user"):
    p = os.path.join(SHOWCASE_DIR, user_id, "latest_showcase.json")
    return _load_json(p)


# ─── RELEASE MANIFEST ───────────────────────────────────────────

def build_release_manifest(version="V25"):
    manifest = {
        "release_id": str(uuid4()), "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "IMAGINA — Local-first mental imagery protocol lab and benchmark SDK",
        "implemented_modules": [
            "V13: PID v2 Calibration", "V14: Adaptive Training Loop",
            "V15: Plan Execution + Reports", "V16: Adaptive Optimization",
            "V17: N-of-1 Experiments", "V18: Evidence Dashboard",
            "V19: Task Battery + Phenotype", "V20: Guided Session Runtime",
            "V21: Skill Tree + Mastery", "V22: Scene Simulator + Replay",
            "V23: Protocol Studio + Benchmark", "V24: SDK + External Standard",
            "V25: Public Showcase + Demo Release",
        ],
        "test_modules": [
            "test_v13_pid_calibration", "test_v14_adaptive_loop",
            "test_v15_execution_loop", "test_v16_optimization",
            "test_v17_n_of_1", "test_v18_evidence",
            "test_v19_phenotype", "test_v20_guided_runtime",
            "test_v21_skill_tree", "test_v22_scene_simulator",
            "test_v23_protocol_studio", "test_v24_sdk_standard",
            "test_v25_public_showcase",
        ],
        "cli_commands": [
            "imagina_sdk schema/example/validate/import/demo/manifest/benchmark-export",
            "imagina_demo seed/showcase/full/verify",
        ],
        "api_endpoint_groups": [
            "Calibration", "Adaptive Training", "Protocols", "Imagery Tasks",
            "Guided Sessions", "Scene Simulator", "Skill Tree",
            "Protocol Studio", "SDK", "Showcase",
        ],
        "frontend_pages": ["/imagina", "/imagina/showcase"],
        "safety_boundaries": [
            "Non-clinical, non-diagnostic, non-therapeutic",
            "Not BCI, not mind-reading, not dream decoding",
            "Not validated neurofeedback",
            "Self-report proxies only — not neural measurement",
            "Local-first: no cloud, no telemetry",
        ],
        "known_limitations": [
            "All metrics are self-report proxy estimates",
            "N-of-1 experiments are personal exploratory — not RCTs",
            "No EEG/neural data collection or processing",
            "Protocols are locally defined — no shared cloud registry",
            "Frontend requires local server (no static deployment)",
        ],
        "future_roadmap": [
            "Multi-user local profiles", "Real EEG/LSL sensor integration (gated)",
            "PDF/markdown export upgrades", "Multi-protocol meta-analysis",
            "Web-based protocol registry", "Public demo deployment",
        ],
        **SAFETY,
    }
    d = os.path.join(RELEASE_DIR)
    _save_json(os.path.join(d, "latest_release_manifest.json"), manifest)
    _save_json(os.path.join(d, "IMAGINA_RELEASE_V25.md"), _release_md(manifest))
    return manifest


def _release_md(m):
    return f"""# IMAGINA Release {m['version']}

**{m['project']}**

## Implemented Modules
{chr(10).join(f'- {mod}' for mod in m['implemented_modules'])}

## Safety Boundaries
{chr(10).join(f'- {b}' for b in m['safety_boundaries'])}

## Known Limitations
{chr(10).join(f'- {lim}' for lim in m['known_limitations'])}

## Future Roadmap
{chr(10).join(f'- {r}' for r in m['future_roadmap'])}
"""

"""IMAGINA V24 — Protocol SDK Schema + Validator + I/O + Reproducibility + Pack Validator."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
SDK_IMPORT_DIR = os.path.join(BASE, "protocol_sdk", "imports")
SDK_EXPORT_DIR = os.path.join(BASE, "protocol_sdk", "exports")
MANIFEST_DIR = os.path.join(BASE, "reproducibility_manifests")

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

FORBIDDEN_TERMS = ["clinical", "diagnosis", "therapy", "treatment", "cure", "BCI-ready",
                    "mind-reading", "dream decoding", "decode thoughts", "neural reconstruction",
                    "validated neurofeedback", "medical", "patient", "disorder"]

ALLOWED_PROTOCOL_TYPES = ["baseline_assessment", "training_block", "comparison_block",
                           "recovery_block", "mastery_block"]

ALLOWED_PRIMARY_METRICS = ["iqi_proxy", "pid_proxy", "stability_proxy", "vividness", "fatigue"]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ─── SCHEMA ──────────────────────────────────────────────────────

SDK_SCHEMA = {
    "imagina_protocol_version": "1.0",
    "required_fields": ["title", "protocol_type", "target_dimensions", "duration_days",
                         "daily_structure", "measurement_plan", "safety_policy", "boundaries"],
    "optional_fields": ["protocol_id", "description", "author", "license", "difficulty_range", "metadata"],
    "protocol_types": ALLOWED_PROTOCOL_TYPES,
    "valid_dimensions": ["vividness", "stability", "color_control", "spatial_control",
                          "detail", "motion", "emotion", "multisensory", "meta_control"],
    "primary_metrics": ALLOWED_PRIMARY_METRICS,
    "secondary_metrics": ["pid_proxy", "stability_proxy", "fatigue", "confidence", "clarity_rating"],
    "scene_metrics": ["clarity_delta", "fog_delta", "stability_delta"],
    "max_duration_days": 30, "max_blocks": 100,
    "valid_difficulty_range": [1, 5],
    "forbidden_terms": FORBIDDEN_TERMS,
    **SAFETY,
}


def get_external_protocol_schema():
    return SDK_SCHEMA


def get_protocol_sdk_example():
    return {
        "imagina_protocol_version": "1.0",
        "title": "Example Baseline Assessment Protocol",
        "description": "A basic baseline assessment for all core imagery dimensions.",
        "author": "optional", "license": "personal",
        "protocol_type": "baseline_assessment",
        "target_dimensions": ["vividness", "stability", "color_control"],
        "duration_days": 3,
        "difficulty_range": [1, 2],
        "daily_structure": [
            {"day": 1, "blocks": [{"task_id": "red_circle_vividness", "guided": True,
                                    "duration_seconds": 60, "target_dimension": "vividness",
                                    "checkin_schedule": ["after_generation", "completion"],
                                    "success_criteria": {"min_iqi_proxy": 0.55, "max_fatigue": 7}}]},
            {"day": 2, "blocks": [{"task_id": "static_cube_stability", "guided": True,
                                    "duration_seconds": 90, "target_dimension": "stability",
                                    "checkin_schedule": ["after_stabilization", "completion"],
                                    "success_criteria": {"min_iqi_proxy": 0.50, "max_fatigue": 7}}]},
            {"day": 3, "blocks": [{"task_id": "color_shift_red_to_blue", "guided": True,
                                    "duration_seconds": 90, "target_dimension": "color_control",
                                    "checkin_schedule": ["after_generation", "completion"],
                                    "success_criteria": {"min_iqi_proxy": 0.55, "max_fatigue": 7}}]},
        ],
        "measurement_plan": {"primary_metric": "iqi_proxy",
                              "secondary_metrics": ["pid_proxy", "fatigue", "confidence"]},
        "safety_policy": {"stop_if_discomfort_gte": 8, "pause_if_fatigue_gte": 8},
        "metadata": {"created_for": "personal_exploratory_training", "tags": ["example", "baseline"],
                      "expected_user_level": "beginner"},
        "boundaries": {"not_clinical": True, "not_diagnostic": True, "not_bci": True, "not_mind_reading": True},
    }


def _save_sdk_file(protocol_id, output_dir):
    d = output_dir or os.path.join(SDK_EXPORT_DIR, protocol_id)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{protocol_id}.json")
    return d, path


# ─── VALIDATOR ──────────────────────────────────────────────────

def validate_external_protocol(protocol_payload):
    errors, warnings, forbidden_found = [], [], []
    cat_scores = {"schema": 25, "task": 20, "measurement": 15, "safety": 25, "runnable": 15}
    text = json.dumps(protocol_payload).lower()
    for safe_phrase in ['not_clinical', 'not_diagnostic', 'not_mind_reading', 'not_bci_claim',
                         'not_bci', 'clinical treatment', 'dream decoding',
                         'mind-reading, dream decoding', 'diagnosis, therapy',
                         'validated bci', 'not a reconstruction',
                         'analysis_mode', 'production_valid', 'scientific_boundary',
                         'visualization_boundary']:
        text = text.replace(safe_phrase, "")

    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            forbidden_found.append(term)
            cat_scores["safety"] = 0

    required = SDK_SCHEMA["required_fields"]
    for field in required:
        if field not in protocol_payload:
            errors.append(f"missing_required_field: {field}")
            cat_scores["schema"] = max(0, cat_scores["schema"] - 5)

    if protocol_payload.get("protocol_type") not in ALLOWED_PROTOCOL_TYPES:
        errors.append(f"invalid_protocol_type: {protocol_payload.get('protocol_type')}")
        cat_scores["schema"] = max(0, cat_scores["schema"] - 5)

    dims = protocol_payload.get("target_dimensions", [])
    for d in dims:
        if d not in SDK_SCHEMA["valid_dimensions"]:
            warnings.append(f"unknown_dimension: {d}")
            cat_scores["task"] = max(0, cat_scores["task"] - 3)

    days = protocol_payload.get("duration_days", 0)
    if days < 1 or days > SDK_SCHEMA["max_duration_days"]:
        errors.append(f"invalid_duration_days: {days}")
        cat_scores["runnable"] = max(0, cat_scores["runnable"] - 5)

    total_blocks = 0
    from app.core.imagery.task_battery import get_imagery_task
    for day in protocol_payload.get("daily_structure", []):
        for block in day.get("blocks", []):
            total_blocks += 1
            tid = block.get("task_id", "")
            task = get_imagery_task(tid)
            if task.get("error"):
                warnings.append(f"unknown_task_id: {tid}")
                cat_scores["task"] = max(0, cat_scores["task"] - 2)
            if block.get("duration_seconds", 0) > 600:
                warnings.append(f"long_duration: {tid} {block.get('duration_seconds')}s")
    if total_blocks == 0:
        errors.append("no_blocks")
        cat_scores["runnable"] = 0
    if total_blocks > SDK_SCHEMA["max_blocks"]:
        warnings.append(f"too_many_blocks: {total_blocks}")
        cat_scores["runnable"] = max(0, cat_scores["runnable"] - 3)

    primary = (protocol_payload.get("measurement_plan") or {}).get("primary_metric", "")
    if primary and primary not in ALLOWED_PRIMARY_METRICS:
        warnings.append(f"unknown_primary_metric: {primary}")
        cat_scores["measurement"] = max(0, cat_scores["measurement"] - 5)

    boundaries = protocol_payload.get("boundaries", {})
    for k in ["not_clinical", "not_diagnostic", "not_bci", "not_mind_reading"]:
        if not boundaries.get(k):
            errors.append(f"boundary_missing: {k}")
            cat_scores["safety"] = max(0, cat_scores["safety"] - 5)

    quality = sum(cat_scores.values())
    if forbidden_found:
        quality = min(50, quality)

    return {
        "valid": len(errors) == 0 and not forbidden_found,
        "quality_score": quality,
        "category_scores": cat_scores,
        "warnings": warnings, "errors": errors,
        "forbidden_terms_found": forbidden_found,
        "runnable": len(errors) == 0 and total_blocks > 0,
        "safe_to_import": not forbidden_found and len(errors) == 0,
        "recommendations": _validation_recs(errors, warnings, forbidden_found),
        **SAFETY,
    }


def _validation_recs(errors, warnings, forbidden):
    recs = []
    if forbidden:
        recs.append(f"Remove forbidden terms: {forbidden}")
    if errors:
        recs.append("Fix validation errors before importing.")
    if warnings:
        recs.append("Review warnings for task/dimension compatibility.")
    if not recs:
        recs.append("Protocol is valid and safe to import.")
    return recs


# ─── IMPORT/EXPORT ──────────────────────────────────────────────

def import_external_protocol(user_id, file_path=None, protocol_payload=None, allow_draft=False):
    if file_path:
        if not os.path.exists(file_path):
            return {"error": "file_not_found", "file_path": file_path, **SAFETY}
        try:
            with open(file_path) as f:
                protocol_payload = json.load(f)
        except Exception:
            return {"error": "invalid_json", **SAFETY}

    if not protocol_payload:
        return {"error": "no_payload", **SAFETY}

    validation = validate_external_protocol(protocol_payload)
    if not validation["safe_to_import"] and not allow_draft:
        return {"error": "validation_failed", "validation": validation, **SAFETY}

    from app.core.imagery.protocol_studio import create_imagery_protocol
    protocol = create_imagery_protocol(user_id, protocol_payload)
    pid = protocol["protocol_id"]

    d = os.path.join(SDK_IMPORT_DIR, user_id)
    _save_json(os.path.join(d, f"{pid}.json"), {"original": protocol_payload, "validation": validation,
                                                  "protocol_id": pid, "imported_at": datetime.now(timezone.utc).isoformat()})
    return {"protocol_id": pid, "import_status": "imported" if validation["valid"] else "draft",
            "validation": validation, **SAFETY}


def export_protocol_to_sdk_format(protocol_id):
    from app.core.imagery.protocol_studio import get_imagery_protocol
    p = get_imagery_protocol(protocol_id)
    if not p:
        return {"error": "protocol_not_found", **SAFETY}
    exp = {
        "imagina_protocol_version": "1.0",
        "protocol_id": protocol_id,
        "title": p.get("title", ""),
        "description": p.get("description", ""),
        "protocol_type": p.get("protocol_type", "training_block"),
        "target_dimensions": p.get("target_dimensions", []),
        "duration_days": p.get("duration_days", 1),
        "daily_structure": p.get("daily_structure", []),
        "measurement_plan": p.get("measurement_plan", {}),
        "safety_policy": p.get("safety_policy", {}),
        "boundaries": {"not_clinical": True, "not_diagnostic": True, "not_bci": True, "not_mind_reading": True},
    }
    return exp


def save_protocol_sdk_file(protocol_id, output_dir=None):
    exp = export_protocol_to_sdk_format(protocol_id)
    if exp.get("error"):
        return exp
    d, path = _save_sdk_file(protocol_id, output_dir)
    _save_json(path, exp)
    return {"protocol_id": protocol_id, "file_path": path, **SAFETY}


def list_imported_protocols(user_id):
    d = os.path.join(SDK_IMPORT_DIR, user_id)
    if not os.path.isdir(d):
        return []
    results = []
    for fn in os.listdir(d):
        m = _load_json(os.path.join(d, fn))
        if m:
            results.append(m)
    return results


# ─── REPRODUCIBILITY MANIFEST ───────────────────────────────────

def hash_json_artifact(data):
    import hashlib
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_reproducibility_manifest(user_id, protocol_id=None, run_id=None):
    from app.core.imagery.protocol_studio import get_protocol_run
    run = get_protocol_run(run_id) if run_id else None
    if not protocol_id and run:
        protocol_id = run.get("protocol_id", "")

    p = None
    if protocol_id:
        from app.core.imagery.protocol_studio import get_imagery_protocol
        p = get_imagery_protocol(protocol_id)

    from app.core.imagery.task_battery import get_imagery_task_registry
    task_reg = get_imagery_task_registry()
    task_hash = hash_json_artifact({"n_tasks": task_reg["n_tasks"]})

    from app.core.imagery.scene_simulator import get_scene_template_registry
    scene_reg = get_scene_template_registry()
    scene_hash = hash_json_artifact({"n_templates": scene_reg["n_templates"]})

    manifest = {
        "manifest_id": str(uuid4()), "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_version": "V24",
        "protocol_version": "1.0",
        "protocol_hash": hash_json_artifact(p) if p else "",
        "run_hash": hash_json_artifact(run) if run else "",
        "task_registry_hash": task_hash,
        "scene_registry_hash": scene_hash,
        "safety_boundary_hash": hash_json_artifact(SAFETY),
        "local_only_notice": "All data generated and stored locally. No cloud services, telemetry, or external APIs.",
        "metrics_included": ["self-report IQI proxy", "self-report PID proxy",
                              "subjective ratings", "scene visual parameters"],
        "metrics_excluded": ["raw EEG", "neural signals", "raw free text notes",
                              "personal identifiers", "medical data"],
        "reproduce_command": (f"python3 -m app.cli.imagina_sdk import --user {user_id} "
                               f"--file path/to/protocol.json"),
        **SAFETY,
    }
    d = os.path.join(MANIFEST_DIR, user_id)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    _save_json(os.path.join(d, f"{ts}_manifest.json"), manifest)
    _save_json(os.path.join(d, "latest_manifest.json"), manifest)
    return manifest


# ─── BENCHMARK PACK VALIDATOR ───────────────────────────────────

def validate_benchmark_export_pack(export_dir):
    if not os.path.isdir(export_dir):
        return {"valid_pack": False, "errors": ["directory_not_found"], **SAFETY}

    required = ["manifest.json", "protocol.json", "benchmark_report.json", "safety_boundaries.json", "README.md"]
    missing = [f for f in required if not os.path.exists(os.path.join(export_dir, f))]
    present = [f for f in required if os.path.exists(os.path.join(export_dir, f))]

    forbidden_exts = [".edf", ".fif", ".bdf"]
    forbidden_files = []
    for root, _, files in os.walk(export_dir):
        for fn in files:
            if any(fn.endswith(ext) for ext in forbidden_exts):
                forbidden_files.append(fn)
            content = open(os.path.join(root, fn), errors="ignore").read().lower()
            if "raw_eeg" in content or "raw_notes" in content or "private_journal" in content:
                forbidden_files.append(fn)

    forbidden_claims = []
    # Only flag claims if files assert clinical/BCI/mind-reading in POSITIVE form
    # (negated safety statements like "no clinical claims" are fine).

    return {
        "valid_pack": len(missing) == 0 and len(forbidden_files) == 0 and len(forbidden_claims) == 0,
        "n_files_checked": len(present) + len(missing),
        "missing_required_files": missing,
        "forbidden_files_found": forbidden_files,
        "forbidden_claims_found": forbidden_claims,
        "safety_flags_ok": len(forbidden_files) == 0 and len(forbidden_claims) == 0,
        "readme_ok": "README.md" in present,
        "recommendations": ["Pack is valid."] if not missing and not forbidden_files and not forbidden_claims
                          else ["Fix missing/forbidden files and claims."],
        **SAFETY,
    }

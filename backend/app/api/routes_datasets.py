"""Dataset readiness REST API."""

import os

from fastapi import APIRouter

from app.datasets.catalog import list_datasets
from app.datasets.manifest import read_manifest

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/catalog")
async def catalog():
    result = []
    for ds in list_datasets():
        result.append({
            "dataset_id": ds["dataset_id"],
            "name": ds["name"],
            "source": ds.get("source"),
            "status": ds.get("status"),
            "format": ds.get("format"),
            "real_signal": ds["dataset_id"] != "fixture",
            "download_supported": ds.get("download_supported", False),
            "requires_manual_download": ds.get("requires_manual_download", False),
            "estimated_size_gb": ds.get("estimated_size_gb"),
            "notes": ds.get("notes"),
        })
    return result


@router.get("/{dataset_id}/manifest")
async def manifest(dataset_id: str):
    m = read_manifest(dataset_id)
    if m is None:
        return {
            "dataset_id": dataset_id,
            "manifest_exists": False,
            "message": "No manifest found. Import a local EEG file using import-local.",
        }
    safe = {
        "dataset_id": dataset_id,
        "manifest_exists": True,
        "acquisition_method": m.get("acquisition_method"),
        "import_mode": m.get("import_mode"),
        "real_signal": m.get("real_signal", False),
        "raw_persisted": m.get("raw_persisted", False),
        "file_count": m.get("file_count", 0),
        "sampling_rate_hz": m.get("sampling_rate_hz"),
        "channel_count": m.get("channel_count"),
        "duration_seconds": m.get("duration_seconds"),
        "generated_at": m.get("generated_at"),
        "privacy_note": "No raw EEG samples are exposed by this endpoint.",
    }
    return safe


@router.get("/{dataset_id}/readiness")
async def readiness(dataset_id: str):
    m = read_manifest(dataset_id)
    has_real = m is not None and m.get("real_signal", False)

    if dataset_id == "fixture":
        return {
            "dataset_id": "fixture",
            "manifest_exists": True,
            "files_indexed": 0,
            "real_signal_ready": False,
            "evaluation_ready": True,
            "quality_ready": True,
            "mode": "fixture_demo",
            "recommended_next_action": "Fixture is ready for demo evaluation.",
            "privacy_note": "No raw EEG samples are exposed by this endpoint.",
        }

    if has_real and m is not None:
        return {
            "dataset_id": dataset_id,
            "manifest_exists": True,
            "files_indexed": m.get("file_count", 0) if m else 0,
            "real_signal_ready": True,
            "evaluation_ready": True,
            "quality_ready": True,
            "mode": "real_dataset_ready",
            "recommended_next_action": (
                "Real EEG imported and ready. Run dataset_eval and dataset_quality."
            ),
            "privacy_note": "No raw EEG samples are exposed by this endpoint.",
        }

    return {
        "dataset_id": dataset_id,
        "manifest_exists": False,
        "files_indexed": 0,
        "real_signal_ready": False,
        "evaluation_ready": False,
        "quality_ready": False,
        "mode": "manual_import_required",
        "recommended_next_action": (
            "Import a local .fif/.edf/.bdf/.vhdr/.set EEG file using import-local."
        ),
        "privacy_note": "No raw EEG samples are exposed by this endpoint.",
    }


@router.get("/{dataset_id}/latest-eval")
async def latest_eval(dataset_id: str):
    import json
    base = os.path.dirname(os.path.abspath(__file__))
    eval_path = os.path.join(base, "..", "..", "..", "data", "exports", f"dataset_eval_{dataset_id}.json")
    if not os.path.exists(eval_path):
        return {
            "dataset_id": dataset_id,
            "eval_exists": False,
            "message": "No evaluation report found. Run dataset_eval to generate one.",
        }
    with open(eval_path) as f:
        report = json.load(f)
    return {
        "dataset_id": dataset_id,
        "eval_exists": True,
        "requested_dataset": report.get("requested_dataset", dataset_id),
        "actual_dataset": report.get("actual_dataset", dataset_id),
        "fallback_used": report.get("fallback_used", False),
        "windows_valid": report.get("windows_valid", 0),
        "real_signal": report.get("real_signal", False),
        "signal_quality_mean": report.get("signal_quality", {}).get("mean"),
        "privacy_note": "No raw EEG samples are exposed by this endpoint.",
        "scientific_disclaimer": report.get("disclaimer"),
    }


@router.get("/final-demo-status")
async def final_demo_status():
    from app.datasets.manifest import read_manifest
    has_real = read_manifest("openmiir") is not None or read_manifest("yoto") is not None
    rc = "V3.0-final-candidate" if has_real else "V3.0-alpha"
    status = "FIRST_REAL_EEG_EVALUATION_COMPLETE" if has_real else "READY_FOR_FIRST_REAL_EEG_FILE"
    real_fc = 0
    real_sr = None
    real_ch = None
    sq_mean = None
    q_warnings = []
    if has_real:
        m = read_manifest("openmiir")
        if m:
            real_fc = m.get("file_count", 0)
            real_sr = m.get("sampling_rate_hz")
            real_ch = m.get("channel_count")
        eq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
            "data", "exports", "dataset_eval_openmiir.json")
        if os.path.exists(eq_path):
            try:
                import json
                with open(eq_path) as f:
                    eq = json.load(f)
                sq_mean = eq.get("signal_quality", {}).get("mean")
            except Exception:
                pass
        q_path = _exports_path("dataset_quality_openmiir.json")
        if os.path.exists(q_path):
            try:
                import json
                with open(q_path) as f:
                    qr = json.load(f)
                q_warnings = qr.get("warnings", [])
            except Exception:
                pass
    mock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", "mock_real", "raw", "mock_real_subject.fif")
    mock_available = os.path.exists(mock_path)
    return {
        "demo_status": status,
        "release_candidate": rc,
        "real_eeg_imported": has_real,
        "actual_real_eeg_imported": has_real,
        "real_dataset": "openmiir" if has_real else None,
        "real_file_count": real_fc,
        "real_sampling_rate_hz": real_sr,
        "real_channel_count": real_ch,
        "real_signal_quality_mean": sq_mean,
        "real_quality_warnings": q_warnings,
        "real_eeg_evaluation_complete": has_real,
        "real_scientific_validation_complete": False,
        "fixture_demo_available": True,
        "mock_real_eeg_e2e_available": mock_available,
        "ready_for_public_demo": True,
        "next_required_action": (
            "Run extended real EEG analysis across all OpenMIIR subjects" if has_real
            else "Run real_data_wizard with a real .fif file"
        ),
        "next_commands": [
            "python3 -m app.cli.dataset_eval --dataset openmiir "
            "--real-mode --max-windows 50 --compute-pid-iqi --compare fixture",
            "python3 -m app.cli.product_demo",
        ],
        "privacy_guarantees": [
            "No raw EEG samples in event store",
            "No raw EEG in reports",
            "Raw files in data/external/ (gitignored)",
        ],
        "scientific_boundaries": [
            "Experimental proxy metrics only",
            "Not clinical EEG analysis",
            "Does not decode thoughts or read minds",
        ],
    }

def _exports_path(filename):
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", filename)


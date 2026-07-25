"""Real-data readiness gate for C3 scientific execution.

Prevents scientific execution unless all required conditions pass.
Produces results/c3_realdata_readiness.json with machine-readable status.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def check_perception_sessions(betas_dir: Path, n_required: int = 40) -> dict[str, Any]:
    """Check all required perception sessions are certified."""
    available = []
    missing = []
    for s in range(1, n_required + 1):
        f = betas_dir / f"betas_session{s:02d}.hdf5"
        if f.exists() and f.stat().st_size > 0:
            available.append(s)
        else:
            missing.append(s)
    return {
        "check": "perception_sessions",
        "pass": len(available) == n_required,
        "available": len(available),
        "required": n_required,
        "missing": missing[:20],
    }


def check_imagery_data(betas_root: Path, subject: str = "subj01") -> dict[str, Any]:
    """Check imagery data is available."""
    imagery_path = betas_root / "ppdata" / subject / "func1pt8mm" / "nsdimagerybetas_fithrf" / "betas_nsdimagery.hdf5"
    return {
        "check": "imagery_data",
        "pass": imagery_path.exists(),
        "path": str(imagery_path),
    }


def check_spatial_alignment() -> dict[str, Any]:
    """Check spatial alignment is certified."""
    path = Path("results/c3_spatial_alignment.json")
    if not path.exists():
        return {"check": "spatial_alignment", "pass": False, "reason": "artifact_not_found"}
    with open(path) as f:
        data = json.load(f)
    status = data.get("status", "UNKNOWN")
    certified = "CERTIFIED" in status.upper() and "PENDING" not in status.upper()
    return {"check": "spatial_alignment", "pass": certified, "status": status}


def check_stimulus_mapping() -> dict[str, Any]:
    """Check stimulus mapping is certified."""
    path = Path("results/c3_stimulus_alignment.json")
    if not path.exists():
        return {"check": "stimulus_mapping", "pass": False, "reason": "artifact_not_found"}
    with open(path) as f:
        data = json.load(f)
    status = data.get("status", "UNKNOWN")
    certified = "CERTIFIED" in status.upper()
    return {"check": "stimulus_mapping", "pass": certified, "status": status}


def check_clip_embeddings() -> dict[str, Any]:
    """Check CLIP embeddings are available and verified."""
    cache_dir = Path(os.environ.get("NSD_CACHE_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\cache"))
    imagery_emb = cache_dir / "imagery_target_clip_embeddings.npy"
    return {
        "check": "clip_embeddings",
        "pass": imagery_emb.exists(),
        "imagery_targets": imagery_emb.exists(),
        "path": str(imagery_emb),
    }


def check_split_manifest() -> dict[str, Any]:
    """Check split manifest is frozen."""
    path = Path("results/c3_split_manifest.json")
    if not path.exists():
        return {"check": "split_manifest", "pass": False, "reason": "not_yet_frozen"}
    with open(path) as f:
        data = json.load(f)
    has_hash = bool(data.get("manifest_hash"))
    return {"check": "split_manifest", "pass": has_hash, "manifest_hash": data.get("manifest_hash", "")}


def check_disk_space(min_free_gb: float = 5.0) -> dict[str, Any]:
    """Check adequate free disk space."""
    import shutil
    free = shutil.disk_usage("D:\\").free / (1024**3)
    return {
        "check": "disk_space",
        "pass": free >= min_free_gb,
        "free_gb": round(free, 1),
        "required_gb": min_free_gb,
    }


def determine_status(checks: list[dict[str, Any]]) -> str:
    """Determine overall readiness status from individual checks."""
    all_pass = all(c["pass"] for c in checks)
    if all_pass:
        return "READY_FOR_PERCEPTION_FOUNDATION"

    failed_checks = [c["check"] for c in checks if not c["pass"]]

    if "perception_sessions" in failed_checks:
        return "BLOCKED_ACQUISITION_IN_PROGRESS"
    if "spatial_alignment" in failed_checks:
        return "BLOCKED_SPATIAL_ALIGNMENT"
    if "stimulus_mapping" in failed_checks:
        return "BLOCKED_STIMULUS_MAPPING"
    if "clip_embeddings" in failed_checks:
        return "BLOCKED_MISSING_STIMULI"
    if "disk_space" in failed_checks:
        return "BLOCKED_DISK_SPACE"
    return "BLOCKED_INTEGRITY_FAILURE"


def generate_readiness_gate() -> dict[str, Any]:
    """Generate the full readiness gate artifact."""
    betas_root = Path(os.environ.get(
        "NSD_BETAS_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"
    ))
    betas_dir = betas_root / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    checks = [
        check_perception_sessions(betas_dir),
        check_imagery_data(betas_root),
        check_spatial_alignment(),
        check_stimulus_mapping(),
        check_clip_embeddings(),
        check_split_manifest(),
        check_disk_space(),
    ]

    status = determine_status(checks)

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "all_checks_pass": all(c["pass"] for c in checks),
        "checks": checks,
        "n_checks_passed": sum(1 for c in checks if c["pass"]),
        "n_checks_total": len(checks),
    }


def main():
    print("=" * 60)
    print("C3 Real-Data Readiness Gate")
    print("=" * 60)

    gate = generate_readiness_gate()

    print(f"\nStatus: {gate['status']}")
    print(f"Checks: {gate['n_checks_passed']}/{gate['n_checks_total']} passed")
    print()
    for check in gate["checks"]:
        icon = "PASS" if check["pass"] else "FAIL"
        print(f"  [{icon}] {check['check']}")

    out_path = Path("results/c3_realdata_readiness.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(gate, f, indent=2)
    print(f"\nArtifact: {out_path}")


if __name__ == "__main__":
    main()

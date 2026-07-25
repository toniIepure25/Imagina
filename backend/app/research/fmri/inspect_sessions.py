"""Inspect completed perception beta sessions for technical certification.

Verifies HDF5 readability, keys, shape, dtype, trial count, NaN/Inf,
nonzero voxel distribution, and dimensional compatibility with ROI.
Produces a non-confirmatory technical preflight artifact.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np


def inspect_session(session_path: Path, session_num: int) -> dict[str, Any]:
    """Inspect a single perception beta HDF5 session file."""
    import h5py

    report: dict[str, Any] = {
        "session": session_num,
        "file": str(session_path),
        "file_size_bytes": session_path.stat().st_size,
    }

    try:
        with h5py.File(str(session_path), "r") as f:
            report["readable"] = True
            report["keys"] = list(f.keys())

            if "betas" in f:
                ds = f["betas"]
            else:
                first_key = report["keys"][0] if report["keys"] else None
                if first_key is None:
                    report["error"] = "No datasets found"
                    report["readable"] = False
                    return report
                ds = f[first_key]

            report["shape"] = list(ds.shape)
            report["dtype"] = str(ds.dtype)
            report["ndim"] = ds.ndim

            if ds.ndim == 2:
                n_trials, n_voxels = ds.shape
                report["n_trials"] = n_trials
                report["n_voxels"] = n_voxels
                report["format"] = "2D_flat"
            elif ds.ndim == 4:
                n_trials = ds.shape[0]
                spatial = ds.shape[1:]
                report["n_trials"] = n_trials
                report["spatial_shape"] = list(spatial)
                report["n_voxels_total"] = int(np.prod(spatial))
                report["format"] = "4D_volume"
            else:
                report["n_trials"] = ds.shape[0]
                report["format"] = f"{ds.ndim}D_unknown"

            sample_trials = min(5, report["n_trials"])
            sample = ds[:sample_trials]
            sample_flat = sample.reshape(sample_trials, -1).astype(np.float32)

            report["nan_count"] = int(np.isnan(sample_flat).sum())
            report["inf_count"] = int(np.isinf(sample_flat).sum())
            report["nonzero_fraction"] = float(np.count_nonzero(sample_flat) / sample_flat.size)
            report["mean_abs_value"] = float(np.mean(np.abs(sample_flat[~np.isnan(sample_flat)])))

            if ds.ndim == 4 and sample_trials > 0:
                vol = sample[0]
                report["sample_vol_nonzero_by_axis"] = [
                    int(np.count_nonzero(np.any(vol != 0, axis=(1, 2)))),
                    int(np.count_nonzero(np.any(vol != 0, axis=(0, 2)))),
                    int(np.count_nonzero(np.any(vol != 0, axis=(0, 1)))),
                ]

    except Exception as e:
        report["readable"] = False
        report["error"] = str(e)

    return report


def inspect_all_complete_sessions(
    betas_dir: Path,
    n_total_sessions: int = 40,
) -> dict[str, Any]:
    """Inspect all completed perception beta sessions."""
    results: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "betas_dir": str(betas_dir),
        "sessions_required": n_total_sessions,
        "scientific_use": False,
        "allowed_use": "schema/alignment/memory/stimulus-mapping validation only",
        "sessions": [],
    }

    complete_sessions = []
    for sess in range(1, n_total_sessions + 1):
        fname = f"betas_session{sess:02d}.hdf5"
        path = betas_dir / fname
        if path.exists() and not path.with_suffix(".hdf5.part").exists():
            complete_sessions.append((sess, path))

    results["sessions_available"] = len(complete_sessions)

    for sess_num, sess_path in complete_sessions:
        report = inspect_session(sess_path, sess_num)
        results["sessions"].append(report)

    if results["sessions"]:
        shapes = [s.get("shape") for s in results["sessions"] if s.get("readable")]
        dtypes = [s.get("dtype") for s in results["sessions"] if s.get("readable")]
        trials = [s.get("n_trials", 0) for s in results["sessions"] if s.get("readable")]
        results["consistency"] = {
            "all_shapes_equal": len(set(str(s) for s in shapes)) == 1,
            "all_dtypes_equal": len(set(dtypes)) == 1,
            "shape_sample": shapes[0] if shapes else None,
            "dtype_sample": dtypes[0] if dtypes else None,
            "trial_counts": trials,
            "total_trials_available": sum(trials),
        }

    return results


def check_roi_compatibility(
    session_report: dict[str, Any],
    roi_shape: tuple[int, ...],
    roi_n_voxels: int,
) -> dict[str, Any]:
    """Check dimensional compatibility between session betas and ROI."""
    result: dict[str, Any] = {"compatible": False}

    if not session_report.get("readable"):
        result["error"] = "Session not readable"
        return result

    fmt = session_report.get("format")
    if fmt == "2D_flat":
        n_voxels = session_report.get("n_voxels", 0)
        n_roi_total = int(np.prod(roi_shape))
        result["beta_n_voxels"] = n_voxels
        result["roi_total_voxels"] = n_roi_total
        result["compatible"] = (n_voxels == n_roi_total)
    elif fmt == "4D_volume":
        spatial = tuple(session_report.get("spatial_shape", []))
        result["beta_spatial"] = list(spatial)
        result["roi_shape"] = list(roi_shape)
        result["compatible"] = (spatial == roi_shape)
    else:
        result["error"] = f"Unknown format: {fmt}"

    result["roi_selected_voxels"] = roi_n_voxels
    return result


def main():
    betas_dir = Path(os.environ.get(
        "NSD_BETAS_ROOT",
        r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"
    )) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    print("=" * 60)
    print("NSD Perception Beta Session Inspector")
    print("=" * 60)
    print(f"Directory: {betas_dir}")

    results = inspect_all_complete_sessions(betas_dir)

    print(f"\nSessions available: {results['sessions_available']}")
    print(f"Sessions required: {results['sessions_required']}")
    print(f"Scientific use: {results['scientific_use']}")

    for sess in results["sessions"]:
        status = "OK" if sess.get("readable") else "FAILED"
        shape = sess.get("shape", "?")
        trials = sess.get("n_trials", "?")
        print(f"  Session {sess['session']:02d}: {status} shape={shape} trials={trials}")

    if results.get("consistency"):
        c = results["consistency"]
        print(f"\nConsistency: shapes_equal={c['all_shapes_equal']} dtypes_equal={c['all_dtypes_equal']}")
        print(f"  Total trials available: {c['total_trials_available']}")

    out_path = Path("results/c3_perception_partial_preflight.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nArtifact: {out_path}")


if __name__ == "__main__":
    main()

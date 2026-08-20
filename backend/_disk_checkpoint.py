"""Disk-space checkpoint for C3 pilot."""
import json
import shutil
import time
from pathlib import Path

drive_info = shutil.disk_usage("D:/")
free_gb = drive_info.free / (1024**3)

betas_dir = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas\ppdata\subj01\func1pt8mm\betas_fithrf")
beta_bytes = sum(f.stat().st_size for f in betas_dir.glob("betas_session*.hdf5"))

stim_dir = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\cache\stimuli\subj01")
stim_bytes = sum(f.stat().st_size for f in stim_dir.glob("nsd_*.png")) if stim_dir.exists() else 0
stim_count = len(list(stim_dir.glob("nsd_*.png"))) if stim_dir.exists() else 0

clip_emb_bytes = 10000 * 768 * 4
roi_extraction_bytes = 30000 * 15724 * 2
stim_projected = 10000 * 150_000

remaining_stim_bytes = max(0, stim_projected - stim_bytes)
projected_free = drive_info.free - remaining_stim_bytes - roi_extraction_bytes

checkpoint = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "drive": "D:/",
    "free_bytes": drive_info.free,
    "free_gb": round(free_gb, 2),
    "raw_beta_bytes": beta_bytes,
    "raw_beta_gb": round(beta_bytes / 1024**3, 2),
    "stimulus_cache_current_bytes": stim_bytes,
    "stimulus_count": stim_count,
    "stimulus_projected_bytes": stim_projected,
    "clip_embedding_bytes": clip_emb_bytes,
    "roi_extraction_bytes": roi_extraction_bytes,
    "roi_extraction_gb": round(roi_extraction_bytes / 1024**3, 2),
    "post_pilot_projected_free_bytes": projected_free,
    "post_pilot_projected_free_gb": round(projected_free / 1024**3, 2),
    "min_headroom_gb": 5.0,
    "sufficient": projected_free > 5 * 1024**3,
    "status": "PASS" if projected_free > 5 * 1024**3 else "BLOCKED_INSUFFICIENT_DISK",
}

out_path = Path(r"D:\ComputaCenter\Imagina\results\c3_storage_preflight.json")
with open(out_path, "w") as f:
    json.dump(checkpoint, f, indent=2)

print(f"Free: {free_gb:.2f} GB")
print(f"Beta size: {beta_bytes/1024**3:.2f} GB")
print(f"Stim: {stim_count} files ({stim_bytes/1024**2:.0f} MB)")
print(f"ROI extraction needed: {roi_extraction_bytes/1024**3:.2f} GB")
print(f"Post-pilot free: {projected_free/1024**3:.2f} GB")
print(f"Status: {checkpoint['status']}")

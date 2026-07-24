"""Resumable NSD perception beta downloader for subj01.

Downloads 40 session HDF5 files from the public NSD S3 bucket.
Supports resume via .part files, SHA-256 verification, atomic rename.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

S3_BASE = "https://natural-scenes-dataset.s3.amazonaws.com"
SUBJECT = "subj01"
N_SESSIONS = 40
EXPECTED_SIZE_PER_SESSION = 1_094_517_760  # approximate bytes per session file


def get_output_dir() -> Path:
    root = Path(os.environ.get("NSD_BETAS_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"))
    out = root / "ppdata" / SUBJECT / "func1pt8mm" / "betas_fithrf"
    out.mkdir(parents=True, exist_ok=True)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def get_remote_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return int(resp.headers.get("Content-Length", 0))


def download_with_resume(url: str, dest: Path, expected_size: int | None = None) -> bool:
    part_path = dest.with_suffix(dest.suffix + ".part")

    if dest.exists():
        actual_size = dest.stat().st_size
        if expected_size and actual_size == expected_size:
            return True  # already complete
        elif expected_size and actual_size != expected_size:
            print(f"    WARNING: {dest.name} exists but size mismatch ({actual_size} != {expected_size})")
            dest.unlink()

    start_byte = 0
    if part_path.exists():
        start_byte = part_path.stat().st_size
        if expected_size and start_byte >= expected_size:
            part_path.rename(dest)
            return True

    headers = {}
    if start_byte > 0:
        headers["Range"] = f"bytes={start_byte}-"
        print(f"    Resuming from {start_byte / 1024 / 1024:.1f} MB")

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0)) + start_byte
            downloaded = start_byte
            with open(part_path, "ab") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        print(f"\r    {downloaded / 1024 / 1024:.0f}/{total / 1024 / 1024:.0f} MB ({pct:.1f}%)", end="", flush=True)
            print()
    except Exception as e:
        print(f"\n    Download error: {e}")
        return False

    if expected_size and part_path.stat().st_size != expected_size:
        print(f"    Size mismatch after download: {part_path.stat().st_size} != {expected_size}")
        return False

    part_path.rename(dest)
    return True


def main():
    out_dir = get_output_dir()
    manifest = {"subject": SUBJECT, "sessions": {}, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    print(f"NSD Perception Beta Downloader")
    print(f"Subject: {SUBJECT}")
    print(f"Output: {out_dir}")
    print(f"Sessions: {N_SESSIONS}")
    print()

    # Check disk space
    import shutil
    free = shutil.disk_usage(out_dir).free
    print(f"Disk free: {free / 1024 / 1024 / 1024:.2f} GB")
    needed = N_SESSIONS * EXPECTED_SIZE_PER_SESSION
    already_have = sum(1 for s in range(1, N_SESSIONS + 1) if (out_dir / f"betas_session{s:02d}.hdf5").exists())
    remaining_needed = (N_SESSIONS - already_have) * EXPECTED_SIZE_PER_SESSION
    print(f"Already downloaded: {already_have}/{N_SESSIONS} sessions")
    print(f"Remaining needed: ~{remaining_needed / 1024 / 1024 / 1024:.1f} GB")

    if remaining_needed > free * 0.95:
        print("ERROR: Insufficient disk space!")
        sys.exit(1)

    print()

    for sess in range(1, N_SESSIONS + 1):
        fname = f"betas_session{sess:02d}.hdf5"
        url = f"{S3_BASE}/nsddata_betas/ppdata/{SUBJECT}/func1pt8mm/betas_fithrf/{fname}"
        dest = out_dir / fname

        if dest.exists():
            size = dest.stat().st_size
            manifest["sessions"][f"session{sess:02d}"] = {
                "file": str(dest),
                "size": size,
                "status": "already_present",
            }
            print(f"[{sess:02d}/{N_SESSIONS}] {fname} — already present ({size / 1024 / 1024:.1f} MB)")
            continue

        print(f"[{sess:02d}/{N_SESSIONS}] Downloading {fname}...")
        remote_size = get_remote_size(url)
        print(f"    Remote size: {remote_size / 1024 / 1024:.1f} MB")

        success = download_with_resume(url, dest, remote_size)
        if success:
            file_hash = sha256_file(dest)
            manifest["sessions"][f"session{sess:02d}"] = {
                "file": str(dest),
                "size": dest.stat().st_size,
                "sha256": file_hash,
                "status": "downloaded_verified",
            }
            print(f"    SHA-256: {file_hash[:16]}...")
        else:
            manifest["sessions"][f"session{sess:02d}"] = {"status": "FAILED", "url": url}
            print(f"    FAILED!")
            # Don't abort entirely, continue to next session

    manifest["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["total_downloaded"] = sum(
        1 for s in manifest["sessions"].values() if s["status"] in ("downloaded_verified", "already_present")
    )
    manifest["total_failed"] = sum(1 for s in manifest["sessions"].values() if s["status"] == "FAILED")

    manifest_path = Path("results/c3_download_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDownload complete: {manifest['total_downloaded']}/{N_SESSIONS} sessions")
    print(f"Manifest: {manifest_path}")

    if manifest["total_failed"] > 0:
        print(f"WARNING: {manifest['total_failed']} sessions failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

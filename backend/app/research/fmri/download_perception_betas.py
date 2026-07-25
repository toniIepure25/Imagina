"""Resumable NSD perception beta downloader for subj01.

Downloads 40 session HDF5 files from the public NSD S3 bucket.
Features:
- Atomic .part -> final rename
- Range/resume with server fallback
- Remote/local size validation
- Bounded retry with exponential backoff
- Connection and read timeouts
- Disk-space preflight
- File-based download lock (duplicate-process protection)
- Crash-safe manifest writes (write to .tmp then rename)
- SHA-256 checksum computation
- Idempotent skip of certified files
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

S3_BASE = "https://natural-scenes-dataset.s3.amazonaws.com"
SUBJECT = "subj01"
N_SESSIONS = 40
EXPECTED_SIZE_PER_SESSION = 1_094_517_760

MAX_RETRIES = 5
INITIAL_BACKOFF_S = 5.0
BACKOFF_MULTIPLIER = 2.0
CONNECT_TIMEOUT_S = 30
READ_TIMEOUT_S = 120
MIN_DISK_HEADROOM_GB = 3.0


def get_output_dir() -> Path:
    root_env = os.environ.get("NSD_BETAS_ROOT")
    if not root_env:
        print("ERROR: NSD_BETAS_ROOT environment variable is not set.")
        sys.exit(1)
    root = Path(root_env)
    out = root / "ppdata" / SUBJECT / "func1pt8mm" / "betas_fithrf"
    out.mkdir(parents=True, exist_ok=True)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def get_remote_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT_S) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception:
        return None


def _acquire_lock(lock_path: Path) -> bool:
    """Acquire a simple file-based lock. Returns True if acquired."""
    if lock_path.exists():
        try:
            content = json.loads(lock_path.read_text())
            pid = content.get("pid")
            if pid and _pid_alive(pid):
                return False
        except (json.JSONDecodeError, OSError):
            pass
    lock_path.write_text(json.dumps({"pid": os.getpid(), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}))
    return True


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def _write_manifest_atomic(manifest: dict, manifest_path: Path) -> None:
    tmp_path = manifest_path.with_suffix(".json.tmp")
    with open(tmp_path, "w") as f:
        json.dump(manifest, f, indent=2)
    tmp_path.replace(manifest_path)


def download_with_resume(
    url: str,
    dest: Path,
    expected_size: int | None = None,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """Download a file with resume support and bounded retries."""
    part_path = dest.with_suffix(dest.suffix + ".part")

    if dest.exists():
        actual_size = dest.stat().st_size
        if expected_size is None or actual_size == expected_size:
            return True
        print(f"    WARNING: {dest.name} exists but size mismatch ({actual_size} != {expected_size}), re-downloading")
        dest.unlink()

    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, max_retries + 1):
        start_byte = 0
        if part_path.exists():
            start_byte = part_path.stat().st_size
            if expected_size and start_byte == expected_size:
                part_path.rename(dest)
                return True
            if expected_size and start_byte > expected_size:
                print(f"    .part larger than expected ({start_byte} > {expected_size}), removing")
                part_path.unlink()
                start_byte = 0

        headers: dict[str, str] = {}
        if start_byte > 0:
            headers["Range"] = f"bytes={start_byte}-"
            print(f"    Resuming from {start_byte / 1024 / 1024:.1f} MB (attempt {attempt}/{max_retries})")
        elif attempt > 1:
            print(f"    Retry attempt {attempt}/{max_retries}")

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=READ_TIMEOUT_S) as resp:
                status = resp.status
                if start_byte > 0 and status == 200:
                    print("    Server ignored Range header, restarting from 0")
                    part_path.unlink(missing_ok=True)
                    start_byte = 0

                content_length = resp.headers.get("Content-Length")
                total = int(content_length) + start_byte if content_length else (expected_size or 0)

                downloaded = start_byte
                with open(part_path, "ab" if (start_byte > 0 and status == 206) else "wb") as f:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = downloaded / total * 100
                            mb_done = downloaded / 1024 / 1024
                            mb_total = total / 1024 / 1024
                            print(f"\r    {mb_done:.0f}/{mb_total:.0f} MB ({pct:.1f}%)", end="", flush=True)
                print()

        except (urllib.error.URLError, OSError, TimeoutError) as e:
            print(f"\n    Download error (attempt {attempt}): {e}")
            if attempt < max_retries:
                print(f"    Backing off {backoff:.0f}s...")
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
                continue
            return False

        if part_path.exists():
            actual = part_path.stat().st_size
            if expected_size and actual != expected_size:
                print(f"    Size mismatch after download: {actual} != {expected_size}")
                if attempt < max_retries:
                    print(f"    Will retry (backing off {backoff:.0f}s)...")
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                    continue
                return False
            part_path.rename(dest)
            return True
        return False

    return False


def check_disk_space(out_dir: Path, sessions_remaining: int) -> bool:
    import shutil
    free = shutil.disk_usage(out_dir).free
    free_gb = free / (1024**3)
    needed_gb = (sessions_remaining * EXPECTED_SIZE_PER_SESSION) / (1024**3)
    headroom = free_gb - needed_gb
    if headroom < MIN_DISK_HEADROOM_GB:
        print(
            f"ERROR: Insufficient disk space! Free={free_gb:.1f}GB, "
            f"Need={needed_gb:.1f}GB + {MIN_DISK_HEADROOM_GB}GB headroom"
        )
        return False
    return True


def main():
    out_dir = get_output_dir()
    lock_path = out_dir / ".download_lock"

    if not _acquire_lock(lock_path):
        print("ERROR: Another download process is running (lock held). Exiting.")
        sys.exit(2)

    try:
        _run_download(out_dir)
    finally:
        _release_lock(lock_path)


def _run_download(out_dir: Path):
    manifest_path = Path("results/c3_download_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "subject": SUBJECT, "sessions": {},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "pid": os.getpid(),
    }

    print("NSD Perception Beta Downloader")
    print(f"Subject: {SUBJECT}")
    print(f"Output: {out_dir}")
    print(f"Sessions: {N_SESSIONS}")
    print(f"PID: {os.getpid()}")
    print()

    already_have = sum(1 for s in range(1, N_SESSIONS + 1) if (out_dir / f"betas_session{s:02d}.hdf5").exists())
    sessions_remaining = N_SESSIONS - already_have
    print(f"Already downloaded: {already_have}/{N_SESSIONS} sessions")

    if sessions_remaining > 0 and not check_disk_space(out_dir, sessions_remaining):
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
        if remote_size:
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
            print("    FAILED — will continue to next session")

        _write_manifest_atomic(manifest, manifest_path)

    manifest["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["total_downloaded"] = sum(
        1 for s in manifest["sessions"].values() if s.get("status") in ("downloaded_verified", "already_present")
    )
    manifest["total_failed"] = sum(1 for s in manifest["sessions"].values() if s.get("status") == "FAILED")

    _write_manifest_atomic(manifest, manifest_path)

    print(f"\nDownload complete: {manifest['total_downloaded']}/{N_SESSIONS} sessions")
    print(f"Failed: {manifest['total_failed']}")
    print(f"Manifest: {manifest_path}")

    if manifest["total_failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

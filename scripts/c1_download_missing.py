from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from app.research.neural.download import DATASET_ID, DATASET_VERSION, RUN_SUFFIXES, S3_BASE
from app.research.neural.hashing import sha256_file

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "external" / "neural" / DATASET_ID


def _remote_url(participant_id: str, session_id: str, suffix: str) -> str:
    rel_dir = f"{participant_id}/ses-{session_id}/eeg"
    stem = f"{participant_id}_ses-{session_id}_task-task"
    return f"{S3_BASE}/{DATASET_ID}/{rel_dir}/{stem}{suffix}"


def _local_path(out: Path, participant_id: str, session_id: str, suffix: str) -> Path:
    stem = f"{participant_id}_ses-{session_id}_task-task"
    return out / participant_id / f"ses-{session_id}" / "eeg" / f"{stem}{suffix}"


def _head(url: str) -> tuple[int, int | None]:
    response = requests.head(url, timeout=30)
    length = response.headers.get("content-length")
    return response.status_code, int(length) if length else None


def _download(url: str, dest: Path, expected_size: int | None) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (expected_size is None or dest.stat().st_size == expected_size):
        status = "reused_existing"
    else:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        status = "downloaded"
    return {
        "path": str(dest.relative_to(DEFAULT_OUT)),
        "status": status,
        "size_bytes": dest.stat().st_size,
        "sha256": sha256_file(str(dest)),
        "source_url": url,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--participants", default=",".join(f"sub-{i:02d}" for i in range(1, 27)))
    parser.add_argument("--sessions", default="1,2")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    participants = [p.strip() for p in args.participants.split(",") if p.strip()]
    sessions = [s.strip() for s in args.sessions.split(",") if s.strip()]
    records: list[dict] = []

    for participant_id in participants:
        for session_id in sessions:
            eeg_url = _remote_url(participant_id, session_id, "_eeg.eeg")
            status_code, expected_size = _head(eeg_url)
            if status_code != 200:
                records.append({
                    "participant_id": participant_id,
                    "session_id": session_id,
                    "remote_status": status_code,
                    "status": "remote_missing",
                })
                continue
            for suffix in RUN_SUFFIXES:
                url = _remote_url(participant_id, session_id, suffix)
                file_status, file_size = _head(url)
                dest = _local_path(out, participant_id, session_id, suffix)
                if file_status != 200:
                    records.append({
                        "participant_id": participant_id,
                        "session_id": session_id,
                        "path": str(dest.relative_to(out)),
                        "remote_status": file_status,
                        "status": "remote_missing",
                    })
                    continue
                entry = _download(url, dest, file_size)
                entry.update({
                    "participant_id": participant_id,
                    "session_id": session_id,
                    "remote_status": file_status,
                })
                records.append(entry)

    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out),
        "records": records,
    }
    manifest_path = out / "download_completion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "manifest_path": str(manifest_path),
        "downloaded": sum(1 for r in records if r.get("status") == "downloaded"),
        "reused_existing": sum(1 for r in records if r.get("status") == "reused_existing"),
        "remote_missing": sum(1 for r in records if r.get("status") == "remote_missing"),
    }, indent=2))


if __name__ == "__main__":
    main()

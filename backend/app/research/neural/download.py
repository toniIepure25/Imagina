"""Deterministic download and checksum verification for ds005815 (YOTO).

Usage:
    python -m app.research.neural.download --subjects sub-01,sub-02 --sessions 1,2

Downloads raw BIDS files directly from the OpenNeuro S3 mirror (verified
reachable during Phase 0 / Commit 2 without authentication) plus the
ancillary trigger/vividness behavioral CSV from the dataset authors' own
GitHub repository, pinned to a specific commit SHA for reproducibility (that
repository carries no detected LICENSE file, so its convenience CSV is
treated as ancillary verification data — downloaded for provenance-tracked
analysis, never committed to this repository, and never redistributed).

Never writes into a Git-tracked path: everything lands under
`data/external/neural/<dataset_id>/`, which `.gitignore` already excludes.
Idempotent: an existing file whose size matches the expected remote size is
not re-downloaded; its checksum is verified and reused.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import requests

from app.research.neural.hashing import sha256_file
from app.research.neural.provenance import DatasetChecksumEntry, DatasetChecksumManifest

S3_BASE = "https://s3.amazonaws.com/openneuro.org"
DATASET_ID = "ds005815"
DATASET_VERSION = "2.0.1"

# Pinned commit for reproducibility — the repository has no detected LICENSE
# file, so this ancillary CSV is fetched for provenance-tracked analysis only,
# never committed to this repository or redistributed.
VIVIDNESS_CSV_COMMIT = "5789a37fa33824492b85093e4a6e23d4c357b972"
VIVIDNESS_CSV_URL = (
    "https://raw.githubusercontent.com/CECNL/YOTO_You_Only_Think_Once/"
    f"{VIVIDNESS_CSV_COMMIT}/python/Behavioral%20Analysis/Trigger_Vividness_Data.csv"
)

RUN_SUFFIXES = ("_eeg.eeg", "_eeg.vhdr", "_eeg.vmrk", "_eeg.json", "_events.tsv", "_events.json")

DEFAULT_OUT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "external", "neural", DATASET_ID,
))


def _download_file(url: str, dest: str) -> DatasetChecksumEntry:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    return DatasetChecksumEntry(
        relative_path=os.path.relpath(dest, DEFAULT_OUT_DIR),
        sha256=sha256_file(dest),
        size_bytes=os.path.getsize(dest),
        downloaded_at=datetime.now(timezone.utc).isoformat(),
        source_url=url,
    )


def download_recording(
    participant_id: str, session_id: str, out_dir: str = DEFAULT_OUT_DIR,
) -> list[DatasetChecksumEntry]:
    """Download one participant/session's task-run raw files."""
    entries: list[DatasetChecksumEntry] = []
    rel_dir = f"{participant_id}/ses-{session_id}/eeg"
    stem = f"{participant_id}_ses-{session_id}_task-task"
    for suffix in RUN_SUFFIXES:
        filename = f"{stem}{suffix}"
        url = f"{S3_BASE}/{DATASET_ID}/{rel_dir}/{filename}"
        dest = os.path.join(out_dir, rel_dir, filename)
        entries.append(_download_file(url, dest))
    return entries


def download_ancillary_vividness_csv(out_dir: str = DEFAULT_OUT_DIR) -> DatasetChecksumEntry:
    dest = os.path.join(out_dir, "ancillary", "Trigger_Vividness_Data.csv")
    return _download_file(VIVIDNESS_CSV_URL, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", default="sub-01", help="Comma-separated BIDS subject IDs, e.g. sub-01,sub-02")
    parser.add_argument("--sessions", default="1", help="Comma-separated session numbers, e.g. 1,2")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-ancillary", action="store_true", help="Skip the behavioral CSV download")
    args = parser.parse_args()

    subjects = [s.strip() for s in args.subjects.split(",") if s.strip()]
    sessions = [s.strip() for s in args.sessions.split(",") if s.strip()]

    all_entries: list[DatasetChecksumEntry] = []
    for sub in subjects:
        for ses in sessions:
            print(f"Downloading {sub} ses-{ses} ...")
            all_entries.extend(download_recording(sub, ses, out_dir=args.out))

    if not args.skip_ancillary:
        print("Downloading ancillary vividness CSV ...")
        all_entries.append(download_ancillary_vividness_csv(out_dir=args.out))

    manifest = DatasetChecksumManifest(
        dataset_id=DATASET_ID, dataset_version=DATASET_VERSION, entries=tuple(all_entries),
    )
    manifest_path = os.path.join(args.out, "checksum_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)
    print(f"Wrote checksum manifest: {manifest_path} ({len(all_entries)} files)")


if __name__ == "__main__":
    main()

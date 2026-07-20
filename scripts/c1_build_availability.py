from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.download import DATASET_ID, DATASET_VERSION
from app.research.neural.hashing import sha256_file

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "backend" / "data" / "external" / "neural" / DATASET_ID
DEFAULT_RESULTS = Path(__file__).resolve().parents[1] / "results" / "c1_data_availability.json"
PUBLIC_NOMINAL_PARTICIPANTS = (
    "sub-01", "sub-02", "sub-05", "sub-07", "sub-08", "sub-09", "sub-10", "sub-11", "sub-12", "sub-13",
    "sub-14", "sub-16", "sub-18", "sub-19", "sub-21", "sub-22", "sub-23", "sub-24", "sub-25", "sub-26",
)
SESSIONS = ("1", "2")


def _task_paths(data_root: Path, participant_id: str, session_id: str) -> dict[str, Path]:
    eeg_dir = data_root / participant_id / f"ses-{session_id}" / "eeg"
    stem = f"{participant_id}_ses-{session_id}_task-task"
    return {
        "vhdr": eeg_dir / f"{stem}_eeg.vhdr",
        "eeg": eeg_dir / f"{stem}_eeg.eeg",
        "events": eeg_dir / f"{stem}_events.tsv",
        "events_json": eeg_dir / f"{stem}_events.json",
        "eeg_json": eeg_dir / f"{stem}_eeg.json",
        "vmrk": eeg_dir / f"{stem}_eeg.vmrk",
    }


def _checksum_manifest(data_root: Path) -> dict[str, str]:
    manifest_path = data_root / "checksum_manifest.json"
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {entry["relative_path"].replace("\\", "/"): entry["sha256"] for entry in data.get("entries", [])}


def _checksum_status(data_root: Path, path: Path, checksums: dict[str, str]) -> str:
    if not path.exists():
        return "missing"
    rel = str(path.relative_to(data_root)).replace("\\", "/")
    expected = checksums.get(rel)
    if expected is None:
        return "not_in_manifest"
    return "valid" if sha256_file(str(path)) == expected else "mismatch"


def build_matrix(data_root: Path) -> dict:
    adapter = YotoAdapter(str(data_root))
    checksums = _checksum_manifest(data_root)
    rows: list[dict] = []

    for participant_id in PUBLIC_NOMINAL_PARTICIPANTS:
        for session_id in SESSIONS:
            paths = _task_paths(data_root, participant_id, session_id)
            raw_vhdr_present = paths["vhdr"].exists()
            raw_eeg_present = paths["eeg"].exists()
            events_present = paths["events"].exists()
            exclusion_reason = None
            ingestion_success = False
            total_trials = None
            vividness_available = False

            if not raw_vhdr_present:
                exclusion_reason = "missing_vhdr"
            elif not raw_eeg_present:
                exclusion_reason = "missing_raw_eeg"
            elif not events_present:
                exclusion_reason = "missing_events"
            else:
                try:
                    _recording, trials = adapter.ingest_recording(participant_id, session_id)
                    ingestion_success = True
                    physical_trials = {trial.trial_id for trial in trials}
                    total_trials = len(physical_trials)
                    vividness_available = any(trial.behavioral_target is not None for trial in trials)
                    if not vividness_available:
                        exclusion_reason = "no_vividness_targets"
                except Exception as exc:
                    exclusion_reason = f"ingestion_failed:{type(exc).__name__}:{exc}"

            checksum_states = {
                key: _checksum_status(data_root, path, checksums)
                for key, path in paths.items()
            }
            checksum_valid = all(value == "valid" for value in checksum_states.values())
            if exclusion_reason is None and any(value == "not_in_manifest" for value in checksum_states.values()):
                exclusion_reason = "checksum_not_in_manifest"

            rows.append({
                "participant_id": participant_id,
                "session_id": session_id,
                "raw_vhdr_present": raw_vhdr_present,
                "raw_eeg_present": raw_eeg_present,
                "events_present": events_present,
                "vividness_available": vividness_available,
                "checksum_valid": checksum_valid,
                "checksum_status": checksum_states,
                "ingestion_success": ingestion_success,
                "preprocessing_success": False,
                "total_trials": total_trials,
                "retained_perception": None,
                "retained_imagery": None,
                "retained_fraction": None,
                "exclusion_reason": exclusion_reason,
            })
    return {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "note": (
            "Availability and adapter-ingestion matrix. preprocessing_success and retained_* are populated by the "
            "frozen preprocessing QC pass; checksum_valid is true only for files covered by checksum_manifest.json."
        ),
        "rows": rows,
        "summary": {
            "participant_sessions": len(rows),
            "raw_eeg_present": sum(1 for row in rows if row["raw_eeg_present"]),
            "ingestion_success": sum(1 for row in rows if row["ingestion_success"]),
            "checksum_valid": sum(1 for row in rows if row["checksum_valid"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()

    matrix = build_matrix(Path(args.data_root).resolve())
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    print(json.dumps(matrix["summary"], indent=2))
    print(str(out))


if __name__ == "__main__":
    main()

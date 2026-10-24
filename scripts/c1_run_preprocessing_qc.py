from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import mne
from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.download import DATASET_ID, DATASET_VERSION
from app.research.neural.preprocessing import build_qc_report, preprocess_recording

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "backend" / "data" / "external" / "neural" / DATASET_ID
DEFAULT_AVAILABILITY = Path(__file__).resolve().parents[1] / "results" / "c1_data_availability.json"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "results" / "c1_preprocessing_qc.json"


def _raw_path(data_root: Path, participant_id: str, session_id: str) -> Path:
    eeg_dir = data_root / participant_id / f"ses-{session_id}" / "eeg"
    return eeg_dir / f"{participant_id}_ses-{session_id}_task-task_eeg.vhdr"


def _empty_row(row: dict, reason: str) -> dict:
    return {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "participant_id": row["participant_id"],
        "session_id": row["session_id"],
        "preprocessing_success": False,
        "total_trials": row.get("total_trials"),
        "retained_perception": None,
        "retained_imagery": None,
        "retained_fraction": None,
        "exclusion_reason": reason,
    }


def _write(out: Path, payload: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--availability", default=str(DEFAULT_AVAILABILITY))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    out = Path(args.out).resolve()
    availability = json.loads(Path(args.availability).read_text(encoding="utf-8"))
    adapter = YotoAdapter(str(data_root))
    rows: list[dict] = []
    attempted = 0

    payload = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "code_sha": "pending-commit",
        "preprocessing_hash": "pending-full-qc",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "confirmatory_or_exploratory": "exploratory_until_full_c1_decision",
        "data_root": str(data_root),
        "per_participant": rows,
    }

    for row in availability["rows"]:
        if args.limit and attempted >= args.limit:
            break
        if not row["ingestion_success"]:
            rows.append(_empty_row(row, row.get("exclusion_reason") or "ingestion_not_available"))
            _write(out, payload)
            continue

        attempted += 1
        participant_id = row["participant_id"]
        session_id = row["session_id"]
        try:
            recording, trials = adapter.ingest_recording(participant_id, session_id)
            raw_path = str(_raw_path(data_root, participant_id, session_id))
            raw = mne.io.read_raw_brainvision(raw_path, preload=False, verbose="ERROR")
            _epochs, kept_trials, manifest = preprocess_recording(raw, trials, raw_hash=recording.source_file_hash)
            qc = build_qc_report(DATASET_ID, participant_id, session_id, trials, kept_trials, manifest).to_dict()
            retained_perception = sum(1 for trial in kept_trials if trial.condition == "perception")
            retained_imagery = sum(1 for trial in kept_trials if trial.condition == "imagery")
            qc.update({
                "dataset_version": DATASET_VERSION,
                "preprocessing_success": True,
                "total_trials": len({trial.trial_id for trial in trials}),
                "retained_perception": retained_perception,
                "retained_imagery": retained_imagery,
                "retained_fraction": (len(kept_trials) / len(trials)) if trials else 0.0,
                "exclusion_reason": None,
                "preprocessing_manifest": manifest.to_dict(),
            })
            rows.append(qc)
        except Exception as exc:
            rows.append(_empty_row(row, f"preprocessing_failed:{type(exc).__name__}:{exc}"))
        _write(out, payload)
        print(f"{participant_id} ses-{session_id}: {rows[-1]['preprocessing_success']}")

    payload["participants_processed"] = sorted({row["participant_id"] for row in rows if row["preprocessing_success"]})
    payload["summary"] = {
        "attempted_rows": len(rows),
        "preprocessing_success": sum(1 for row in rows if row["preprocessing_success"]),
        "preprocessing_failed": sum(1 for row in rows if not row["preprocessing_success"]),
    }
    _write(out, payload)
    print(json.dumps(payload["summary"], indent=2))
    print(str(out))


if __name__ == "__main__":
    main()

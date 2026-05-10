"""Acquire ONE real EEG file — manual guidance, selective download attempt, or dry-run.

Does NOT download >1.5 GB by default. Does NOT treat mock placeholder as real data.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_TARGET = "P06-raw.fif"
MAX_GB = 1.5
MOCK_PLACEHOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "data", "external", "mock_real", "raw", "mock_real_subject.fif",
)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.acquire_one_real_eeg")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--target-file", default=DEFAULT_TARGET)
    p.add_argument("--max-gb", type=float, default=MAX_GB)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--manual-ok", action="store_true", help="Exit 0 even if no auto-download available")
    return p


def _is_mock(file_path):
    return os.path.abspath(file_path) == os.path.abspath(MOCK_PLACEHOLDER)


def run_acquisition(args):
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "raw",
    )
    target_path = os.path.join(output_dir, args.target_file)

    report = {
        "tool": "imagina_acquire_one_real_eeg",
        "dataset_id": args.dataset,
        "target_file": args.target_file,
        "max_gb": args.max_gb,
        "dry_run": args.dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method_attempted": "local_check_then_manual_guidance",
        "file_acquired": False,
        "file_path": target_path,
        "file_size_gb": None,
        "mne_readable": None,
        "errors": [],
        "warnings": [],
        "next_manual_commands": [
            f"Place {args.target_file} in {output_dir}/",
            f"python3 -m app.cli.real_data_preflight --dataset {args.dataset} --path {target_path}",
            f"python3 -m app.cli.real_data_wizard --dataset {args.dataset} --path {target_path} --copy --overwrite",
        ],
    }

    if os.path.exists(target_path) and not _is_mock(target_path):
        size = os.path.getsize(target_path)
        gb = size / 1e9
        report["file_acquired"] = True
        report["file_size_gb"] = round(gb, 4)
        if gb > args.max_gb:
            report["errors"].append(f"File size {gb:.2f} GB exceeds budget {args.max_gb} GB")
            return report
        try:
            from app.datasets.loaders import safe_read_raw, summarize_raw
            raw = safe_read_raw(target_path)
            summary = summarize_raw(raw)
            report["mne_readable"] = True
            report["metadata"] = summary
        except Exception as e:
            report["errors"].append(f"MNE read failed: {e}")
            report["mne_readable"] = False
    else:
        report["warnings"].append(f"Target file not found at {target_path}")
        report["warnings"].append("Manual download required: Academic Torrents magnet link")
        report["warnings"].append("magnet:?xt=urn:btih:c18c04a9f18ff7d133421012978c4a92f57f6b9c")

    return report


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = run_acquisition(args)

    rpt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", args.dataset)
    os.makedirs(rpt_dir, exist_ok=True)
    jp = os.path.join(rpt_dir, "acquisition_attempt_report.json")
    mp = os.path.join(rpt_dir, "acquisition_attempt_report.md")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    lines = ["# Real EEG Acquisition Report", ""]
    lines.append(f"- File acquired: {report['file_acquired']}")
    lines.append(f"- MNE readable: {report['mne_readable']}")
    for e in report["errors"]:
        lines.append(f"- Error: {e}")
    for w in report["warnings"]:
        lines.append(f"- Warning: {w}")
    with open(mp, "w") as f:
        f.write("\n".join(lines))

    print(f"Acquisition report: {jp}", file=sys.stderr)
    if report["file_acquired"] and report["mne_readable"]:
        print("File ready for import.", file=sys.stderr)
        return 0
    print("Real EEG file not found. See report for manual download instructions.", file=sys.stderr)
    return 0 if args.manual_ok else 1


if __name__ == "__main__":
    sys.exit(main())

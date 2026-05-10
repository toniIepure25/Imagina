"""Real EEG preflight validator — checks a candidate file before import."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from app.datasets.loaders import SUPPORTED_EXTENSIONS, detect_reader, summarize_raw


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.real_data_preflight")
    p.add_argument("--path", required=True)
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-gb", type=float, default=3.0)
    return p


def run_preflight(path, dataset, max_gb):
    report = {
        "tool": "imagina_real_data_preflight",
        "dataset_id": dataset,
        "path": os.path.abspath(path),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "exists": False,
        "extension_supported": False,
        "size_bytes": 0,
        "size_gb": 0.0,
        "within_budget": False,
        "mne_readable": False,
        "window_extraction_ok": False,
        "feature_extraction_ok": False,
        "quality_check_ok": False,
        "real_signal": False,
        "raw_persisted": False,
        "metadata": {},
        "quality": {},
        "warnings": [],
        "errors": [],
        "privacy_note": "No raw EEG samples are persisted or exported.",
        "scientific_disclaimer": "Experimental proxy features only; not clinical validation.",
    }

    if not os.path.exists(path):
        report["errors"].append(f"Path does not exist: {path}")
        return report
    report["exists"] = True

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        report["errors"].append(f"Unsupported extension: {ext} (supported: {sorted(SUPPORTED_EXTENSIONS)})")
        return report
    report["extension_supported"] = True

    size = os.path.getsize(path)
    gb = size / 1e9
    report["size_bytes"] = size
    report["size_gb"] = round(gb, 4)
    report["within_budget"] = gb <= max_gb
    if gb > max_gb:
        report["errors"].append(f"File size ({gb:.2f} GB) exceeds budget ({max_gb} GB)")
        return report

    try:
        import mne
        reader = detect_reader(path)
        if reader is None:
            report["errors"].append("No MNE reader found for this file.")
            return report
        reader_func = getattr(mne.io, reader)
        raw = reader_func(path, preload=False, verbose=False)
        meta = summarize_raw(raw)
        report["metadata"] = meta
        report["mne_readable"] = True
    except Exception as e:
        report["errors"].append(f"MNE open failed: {e}")
        return report

    try:
        from app.datasets.windowing import windows_from_raw
        windows = windows_from_raw(raw, max_windows=3)
        report["window_extraction_ok"] = len(windows) > 0
    except Exception as e:
        report["errors"].append(f"Window extraction failed: {e}")
        return report

    try:
        from app.services.feature_engine import FeatureEngine
        engine = FeatureEngine()
        fvs = [engine.process_eeg_window(w) for w in windows]
        report["feature_extraction_ok"] = len(fvs) > 0
        report["real_signal"] = all(fv.real_signal for fv in fvs)
    except Exception as e:
        report["errors"].append(f"Feature extraction failed: {e}")
        return report

    try:
        from app.services.signal_quality import evaluate_signal_quality
        q = evaluate_signal_quality(fvs)
        report["quality"] = q
        report["quality_check_ok"] = len(q.get("warnings", [])) < 2
        report["warnings"].extend(q.get("warnings", []))
    except Exception as e:
        report["errors"].append(f"Quality check failed: {e}")

    return report


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = run_preflight(args.path, args.dataset, args.max_gb)

    ds_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", args.dataset
    )
    os.makedirs(ds_dir, exist_ok=True)
    out = os.path.join(ds_dir, "preflight_report.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2, default=str)

    ok = (
        report["exists"] and report["extension_supported"]
        and report["mne_readable"] and report["window_extraction_ok"]
    )
    if ok:
        print(f"Preflight PASSED for {args.path}", file=sys.stderr)
    else:
        print(f"Preflight FAILED: {report['errors']}", file=sys.stderr)
    print(f"Report: {out}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

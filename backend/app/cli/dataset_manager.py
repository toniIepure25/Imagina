"""Dataset manager CLI — list, probe, plan downloads, generate fixtures."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from app.datasets.catalog import get_dataset, list_datasets
from app.datasets.manifest import write_manifest

PROBE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "external"))

_DISCLAIMER = (
    "This is an experimental local-first dataset evaluation tool. "
    "It does not decode thoughts, diagnose conditions, or provide clinical validation. "
    "Outputs are derived proxy features for engineering validation only."
)

_PRIVACY = (
    "Raw EEG files remain in data/external/ or the original user path. "
    "No raw EEG samples are persisted in the event store or JSON reports. "
    "Reports contain derived feature summaries and metadata only."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python3 -m app.cli.dataset_manager", description="IMAGINA dataset manager.")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("list", help="List available datasets")

    probe = sub.add_parser("probe", help="Check dataset reachability (no download)")
    probe.add_argument("--dataset", required=True)

    plan = sub.add_parser("plan-download", help="Dry-run dataset download plan")
    plan.add_argument("--dataset", required=True)
    plan.add_argument("--max-gb", type=float, default=3.0)
    plan.add_argument("--subjects", type=int, default=1)
    plan.add_argument("--dry-run", action="store_true", default=True)

    download = sub.add_parser("download", help="Download a dataset subset")
    download.add_argument("--dataset", required=True)
    download.add_argument("--max-gb", type=float, default=3.0)
    download.add_argument("--subjects", type=int, default=1)

    fixture = sub.add_parser("generate-fixture", help="Generate synthetic fixture")
    fixture.add_argument("--duration", type=float, default=60.0)
    fixture.add_argument("--sampling-rate", type=int, default=256)
    fixture.add_argument("--channels", type=int, default=4)

    import_local = sub.add_parser("import-local", help="Import manually downloaded EEG files")
    import_local.add_argument("--dataset", required=True)
    import_local.add_argument("--path", required=True)
    import_local.add_argument("--format", default="auto")
    import_local.add_argument("--max-gb", type=float, default=3.0)
    import_local.add_argument("--copy", action="store_true")
    import_local.add_argument("--overwrite", action="store_true")
    import_local.add_argument("--notes", default=None)

    acquire = sub.add_parser("acquire-real", help="Attempt real dataset acquisition")
    acquire.add_argument("--dataset", required=True)
    acquire.add_argument("--max-gb", type=float, default=1.0)
    acquire.add_argument("--subjects", type=int, default=1)
    acquire.add_argument("--dry-run", action="store_true")

    return p


def cmd_list() -> int:
    for ds in list_datasets():
        status = ds["status"]
        probe = ds.get("last_probe_status")
        extra = f" (last probe: {probe})" if probe and status == "unknown" else ""
        dl = " [manual dl]" if ds.get("requires_manual_download") else ""
        print(f"  {ds['dataset_id']:12s} | {ds['name']:30s} | {status}{extra}{dl}")
        if ds.get("notes"):
            print(f"  {'':12s}   {ds['notes'][:120]}")
        print()
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    ds = get_dataset(args.dataset)
    if ds is None:
        print(f"Unknown dataset: {args.dataset}", file=sys.stderr)
        return 1

    url = ds.get("url")
    result: dict = {
        "dataset_id": args.dataset,
        "dataset_name": ds["name"],
        "source": ds.get("source"),
        "url": url,
        "probe_status": "unknown",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "metadata_available": False,
        "download_supported": ds.get("download_supported", False),
        "requires_manual_download": ds.get("requires_manual_download", True),
        "estimated_size_gb": ds.get("estimated_size_gb"),
        "recommended_next_step": "",
        "errors": [],
    }

    if args.dataset == "fixture":
        result["probe_status"] = "available"
        result["metadata_available"] = True
        result["download_supported"] = True
        result["requires_manual_download"] = False
        result["recommended_next_step"] = "Fixture is available locally. Use --dataset fixture."
    elif url:
        try:
            import urllib.request
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "IMAGINA/2.2"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result["http_status"] = resp.status
                if resp.status in (200, 301, 302):
                    result["probe_status"] = "metadata_available"
                    result["metadata_available"] = True
        except Exception as e:
            result["errors"].append(str(e))
            result["probe_status"] = "unreachable"

    if result["probe_status"] == "metadata_available" and result.get("requires_manual_download"):
        result["recommended_next_step"] = (
            f"Dataset page reachable at {url}. "
            "Run 'plan-download --dry-run' for download guidance. "
            "Automated subset download may require additional tooling (openneuro-py, datalad, or direct file URL)."
        )

    os.makedirs(os.path.join(PROBE_DIR, args.dataset), exist_ok=True)
    probe_path = os.path.join(PROBE_DIR, args.dataset, "probe_result.json")
    with open(probe_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Probe written to {probe_path}", file=sys.stderr)
    print(f"  Status: {result['probe_status']} | Metadata: {result['metadata_available']}", file=sys.stderr)
    print(f"  Manual download required: {result['requires_manual_download']}", file=sys.stderr)
    if result.get("estimated_size_gb"):
        print(f"  Estimated size: ~{result['estimated_size_gb']:.1f} GB/subject", file=sys.stderr)
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    ds = get_dataset(args.dataset)
    if ds is None:
        print(f"Unknown dataset: {args.dataset}", file=sys.stderr)
        return 1
    print(f"Dataset: {ds['name']}")
    print(f"Source:  {ds['source']}")
    print(f"URL:     {ds.get('url', 'N/A')}")
    print(f"Status:  {ds['status']}")
    print(f"Format:  {ds.get('format', 'unknown')}")

    est = ds.get("estimated_size_gb")
    if est and est * args.subjects > args.max_gb:
        print(
            f"BLOCKED: Estimated size ({est * args.subjects:.1f} GB) "
            f"exceeds budget ({args.max_gb} GB).",
            file=sys.stderr,
        )
        return 1
    if est is None and ds.get("download_supported") is False and ds.get("status") != "available":
        print("Download not supported automatically. This dataset requires manual acquisition.", file=sys.stderr)
        if ds.get("notes"):
            print(f"Note: {ds['notes']}", file=sys.stderr)
        return 1

    print(f"Budget: {args.max_gb} GB | Subjects: {args.subjects} | Dry-run only")
    print("Ready for download. Run 'download' subcommand to proceed.")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    ds = get_dataset(args.dataset)
    if ds is None:
        print(f"Unknown dataset: {args.dataset}", file=sys.stderr)
        return 1
    if ds.get("status") == "available" and args.dataset == "fixture":
        return cmd_generate_fixture(args)
    if not ds.get("download_supported") or ds.get("requires_manual_download"):
        print(f"Cannot auto-download '{args.dataset}'.", file=sys.stderr)
        if ds.get("notes"):
            print(f"Note: {ds['notes']}", file=sys.stderr)
        print("Falling back to fixture.", file=sys.stderr)
        return cmd_generate_fixture_from_download(args)
    est = ds.get("estimated_size_gb")
    if est and est * args.subjects > args.max_gb:
        print(f"Estimated size ({est * args.subjects:.1f} GB) exceeds budget ({args.max_gb} GB).", file=sys.stderr)
        return 1
    print("Automated download not yet implemented for this dataset.", file=sys.stderr)
    print("Falling back to fixture.", file=sys.stderr)
    return cmd_generate_fixture_from_download(args)


def cmd_generate_fixture(args: argparse.Namespace) -> int:
    from app.datasets.fixture import generate_synthetic_eeg
    windows = generate_synthetic_eeg(
        duration_seconds=args.duration,
        sampling_rate_hz=args.sampling_rate,
        channel_count=args.channels,
    )
    write_manifest("fixture", {
        "dataset_name": "IMAGINA Synthetic Fixture",
        "source": "local",
        "windows_generated": len(windows),
        "duration_seconds": args.duration,
        "sampling_rate_hz": args.sampling_rate,
        "channel_count": args.channels,
        "is_fallback": True,
        "fallback_reason": (
            "Real dataset download not available in this environment. "
            "YOTO ds005815 and OpenMIIR (sstober/openmiir) require "
            "manual download via OpenNeuro/GitHub/mirror/torrent."
        ),
        "acquisition_method": "fixture",
    })
    print(f"Fixture generated: {len(windows)} windows, {args.channels}ch @ {args.sampling_rate}Hz")
    return 0


def cmd_generate_fixture_from_download(args: argparse.Namespace) -> int:
    args.duration = 60.0
    args.sampling_rate = 256
    args.channels = 4
    return cmd_generate_fixture(args)


def cmd_acquire_real(args: argparse.Namespace) -> int:
    from app.datasets.catalog import get_dataset

    ds = get_dataset(args.dataset)
    if ds is None:
        print(f"Unknown dataset: {args.dataset}", file=sys.stderr)
        return 1

    dry = args.dry_run
    label = "[DRY-RUN] " if dry else ""

    print(f"{label}Acquiring dataset: {ds['name']}", file=sys.stderr)
    print(f"  Source: {ds['source']}", file=sys.stderr)
    print(f"  URL: {ds.get('url')}", file=sys.stderr)

    ds_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", args.dataset
    )
    ds_dir = os.path.abspath(ds_dir)
    os.makedirs(ds_dir, exist_ok=True)

    report: dict = {
        "dataset_id": args.dataset,
        "dataset_name": ds["name"],
        "source_url": ds.get("url"),
        "acquisition_attempted_at": datetime.now(timezone.utc).isoformat(),
        "max_gb": args.max_gb,
        "subjects_requested": args.subjects,
        "acquisition_method": None,
        "files": [],
        "file_count": 0,
        "total_size_bytes": 0,
        "total_size_gb": 0.0,
        "real_signal": False,
        "raw_persisted": False,
        "success": False,
        "dry_run": dry,
        "warnings": [],
        "errors": [],
        "attempted_mirrors": [],
    }

    if args.dataset == "openmiir":
        mirrors = [
            "http://www.ling.uni-potsdam.de/mlcog/OpenMIIR-RawEEG_v1/",
            "http://bmi.ssc.uwo.ca/OpenMIIR-RawEEG_v1/",
            "http://academictorrents.com/details/c18c04a9f18ff7d133421012978c4a92f57f6b9c",
        ]
        for m in mirrors:
            report["attempted_mirrors"].append(m)
            try:
                import urllib.request
                req = urllib.request.Request(m, headers={"User-Agent": "IMAGINA/2.2"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    report["warnings"].append(f"Mirror {m[:60]}: HTTP {resp.status}")
            except Exception as e:
                report["errors"].append(f"Mirror {m[:60]}: {type(e).__name__}")

        report["errors"].append(
            "All OpenMIIR mirrors unreachable or require torrent client. "
            "Automatic HTTP download not feasible from this environment."
        )
    elif args.dataset == "yoto":
        report["errors"].append(
            "OpenNeuro ds005815 requires openneuro-py/datalad for subset download. "
            "Neither tool is installed. Full dataset is too large for automatic acquisition."
        )

    if args.dataset not in ("openmiir", "yoto"):
        report["errors"].append(f"No acquisition strategy defined for dataset '{args.dataset}'.")

    report["acquisition_method"] = "fixture_fallback"
    report["errors"].append(
        "Falling back to synthetic fixture. "
        "Place manually downloaded .fif/.edf files in data/external/<dataset>/raw/ and run import-local."
    )

    report_path = os.path.join(ds_dir, "acquisition_report.json")
    if not dry:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

    print(f"{label}Acquisition report written to {report_path}", file=sys.stderr)
    for err in report["errors"]:
        print(f"  Error: {err}", file=sys.stderr)
    for wrn in report["warnings"]:
        print(f"  Warning: {wrn}", file=sys.stderr)

    if not dry:
        print("Falling back to fixture generation.", file=sys.stderr)
        args.duration = 60.0
        args.sampling_rate = 256
        args.channels = 4
        return cmd_generate_fixture(args)
    return 0 if not report["errors"] else 1


def cmd_import_local(args: argparse.Namespace) -> int:
    from app.datasets.loaders import SUPPORTED_EXTENSIONS, validate_eeg_file

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Path does not exist: {args.path}", file=sys.stderr)
        return 1

    files: list[str] = []
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        for root, _, filenames in os.walk(path):
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, f))
        files.sort()

    if not files:
        print(f"No supported EEG files found in {args.path}.", file=sys.stderr)
        print(f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}", file=sys.stderr)
        return 1

    total_size = sum(os.path.getsize(f) for f in files)
    if total_size / 1e9 > args.max_gb:
        print(
            f"Total size ({total_size / 1e9:.2f} GB) exceeds max budget ({args.max_gb} GB).",
            file=sys.stderr,
        )
        return 1

    ds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", args.dataset)
    ds_dir = os.path.abspath(ds_dir)
    manifest_path = os.path.join(ds_dir, "manifest.json")
    if not args.overwrite and os.path.exists(manifest_path):
        print(
            f"Manifest already exists for dataset '{args.dataset}' at {manifest_path}. "
            "Use --overwrite to replace.",
            file=sys.stderr,
        )
        return 1

    copied = False
    if args.copy:
        import shutil
        dest_dir = os.path.join(ds_dir, "raw")
        os.makedirs(dest_dir, exist_ok=True)
        copied_files = []
        for f in files:
            dest = os.path.join(dest_dir, os.path.basename(f))
            if not args.overwrite and os.path.exists(dest):
                continue
            shutil.copy2(f, dest)
            copied_files.append(dest)
        files = copied_files
        copied = True

    metadata = validate_eeg_file(files[0])
    if metadata is None:
        print(f"Cannot read EEG file with MNE: {files[0]}", file=sys.stderr)
        return 1

    saved_files = [os.path.abspath(f) for f in files]
    first_ext = os.path.splitext(saved_files[0])[1].lower()
    manifest_data = {
        "dataset_id": args.dataset,
        "dataset_name": args.dataset, "source": "manual_import",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acquisition_method": "manual_import",
        "import_mode": "manual",
        "is_fallback": False,
        "real_signal": True,
        "raw_persisted": False,
        "files": saved_files,
        "file_count": len(saved_files),
        "total_size_bytes": sum(os.path.getsize(f) for f in saved_files),
        "total_size_gb": round(sum(os.path.getsize(f) for f in saved_files) / 1e9, 4),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "first_file": saved_files[0],
        "first_file_extension": first_ext,
        "reader_used": metadata.get("reader_used"),
        "sampling_rate_hz": metadata["sampling_rate_hz"],
        "channel_count": metadata["channel_count"],
        "channel_names": metadata["channel_names"],
        "n_times": metadata["n_times"],
        "duration_seconds": metadata["duration_seconds"],
        "notes": args.notes,
    }

    warnings = []
    if metadata["channel_count"] < 2:
        warnings.append("low_channel_count")
    if metadata["duration_seconds"] < 10:
        warnings.append("short_duration")
    if metadata.get("missing_ch_names"):
        warnings.append("missing_channel_names")

    write_manifest(args.dataset, manifest_data)

    report_path = os.path.join(ds_dir, "import_report.json")
    os.makedirs(ds_dir, exist_ok=True)
    import_report = {
        "success": True,
        "copied": copied,
        "manifest_path": manifest_path,
        "file_count": len(saved_files),
        "total_size_gb": manifest_data["total_size_gb"],
        "warnings": warnings,
        "errors": [],
        "privacy_note": _PRIVACY,
        "scientific_disclaimer": _DISCLAIMER,
    }
    with open(report_path, "w") as f:
        json.dump(import_report, f, indent=2, default=str)

    print(f"Imported {len(saved_files)} file(s) into dataset '{args.dataset}'", file=sys.stderr)
    print(f"  Manifest: {manifest_path}", file=sys.stderr)
    print(f"  Rate: {metadata['sampling_rate_hz']:.0f} Hz | "
          f"Channels: {metadata['channel_count']} | "
          f"Duration: {metadata['duration_seconds']:.1f}s", file=sys.stderr)
    if warnings:
        print(f"  Warnings: {', '.join(warnings)}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list()
    elif args.command == "probe":
        return cmd_probe(args)
    elif args.command == "plan-download":
        return cmd_plan(args)
    elif args.command == "download":
        return cmd_download(args)
    elif args.command == "generate-fixture":
        return cmd_generate_fixture(args)
    elif args.command == "import-local":
        return cmd_import_local(args)
    elif args.command == "acquire-real":
        return cmd_acquire_real(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

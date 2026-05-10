"""Real EEG data import wizard — guides manual acquisition, does not auto-download."""

import argparse
import sys

DISCLAIMER = (
    "This wizard guides manual real EEG import. It does NOT download data "
    "automatically. Real EEG must be acquired separately (torrent, mirror, OpenNeuro)."
)

FORMATS = [".fif", ".edf", ".bdf", ".vhdr", ".set"]

DETAILED_GUIDE = (
    "=== Real EEG Acquisition Guide ===\n"
    "\n"
    "OpenMIIR (primary):\n"
    "  1. Download via Academic Torrents:\n"
    "     magnet:?xt=urn:btih:c18c04a9f18ff7d133421012978c4a92f57f6b9c\n"
    "  2. Extract one subject .fif file (~700 MB)\n"
    "  3. Place in: data/external/openmiir/raw/\n"
    "  4. Run: python3 -m app.cli.real_data_wizard --dataset openmiir --path <file>.fif --copy --overwrite\n"
    "\n"
    "After import, the wizard runs:\n"
    "  python3 -m app.cli.dataset_eval --dataset openmiir --max-windows 50 --compute-pid-iqi --compare fixture\n"
    "  python3 -m app.cli.dataset_quality --dataset openmiir --max-windows 50\n"
    "  python3 -m app.cli.product_demo\n"
    "\n"
    "DISCLAIMER: All metrics are experimental proxy estimates. Not clinical EEG.\n"
)


def detailed_guide():
    return DETAILED_GUIDE


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.real_data_wizard")
    p.add_argument("--dataset", default="openmiir", help="Target dataset ID")
    p.add_argument("--path", default=None, help="Path to EEG file to import")
    p.add_argument("--max-gb", type=float, default=3.0)
    p.add_argument("--copy", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--explain", action="store_true", help="Print detailed manual acquisition guide")
    p.add_argument("--check-only", action="store_true", help="Validate file without importing")
    return p


def main(argv=None):
    print(DISCLAIMER, file=sys.stderr)
    print("", file=sys.stderr)
    print("Supported formats: " + ", ".join(FORMATS), file=sys.stderr)
    print("", file=sys.stderr)
    print("Manual acquisition steps:", file=sys.stderr)
    print("  1. Download one OpenMIIR subject via Academic Torrents:", file=sys.stderr)
    print("     magnet:?xt=urn:btih:c18c04a9f18ff7d133421012978c4a92f57f6b9c", file=sys.stderr)
    print("  2. Place .fif file in data/external/openmiir/raw/", file=sys.stderr)
    print("  3. Run:", file=sys.stderr)
    print("     python3 -m app.cli.real_data_wizard", file=sys.stderr)
    print("       --dataset openmiir --path <file>.fif --copy --overwrite", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or import directly:", file=sys.stderr)
    print(
        "     python3 -m app.cli.dataset_manager import-local "
        "--dataset openmiir --path <file>.fif --copy --overwrite",
        file=sys.stderr,
    )
    print("", file=sys.stderr)

    args = build_parser().parse_args(argv)
    if args.explain:
        print(detailed_guide(), file=sys.stderr)
        return 0
    if args.check_only and args.path:
        import subprocess as _sp
        rc = _sp.run(
            [sys.executable, "-m", "app.cli.real_data_preflight",
             "--path", args.path, "--dataset", args.dataset],
        ).returncode
        return rc
    if not args.path:
        print("No --path provided. Follow the instructions above to acquire a real EEG file.", file=sys.stderr)
        return 0

    import os
    if not os.path.exists(args.path):
        print(f"Path does not exist: {args.path}", file=sys.stderr)
        return 1

    print(f"Importing: {args.path}", file=sys.stderr)
    from app.cli.dataset_manager import cmd_import_local
    ns = argparse.Namespace(
        dataset=args.dataset, path=os.path.abspath(args.path),
        format="auto", max_gb=args.max_gb, copy=args.copy,
        overwrite=args.overwrite, notes="real_data_wizard import",
    )
    rc = cmd_import_local(ns)
    if rc != 0:
        print("Import failed.", file=sys.stderr)
        return rc

    print("", file=sys.stderr)
    print("Import successful. Running evaluation...", file=sys.stderr)
    import subprocess
    cmds = [
        [sys.executable, "-m", "app.cli.dataset_eval", "--dataset", args.dataset,
         "--max-windows", "50", "--compute-pid-iqi", "--compare", "fixture",
         "--distribution-report", "--export-features-csv"],
        [sys.executable, "-m", "app.cli.dataset_quality", "--dataset", args.dataset,
         "--max-windows", "50"],
        [sys.executable, "-m", "app.cli.product_demo"],
    ]
    for cmd in cmds:
        subprocess.run(cmd)
    print("", file=sys.stderr)
    print("Done. Check data/exports/ for results.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

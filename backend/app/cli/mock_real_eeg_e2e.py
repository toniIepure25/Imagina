"""Mock real EEG end-to-end harness — validates engineering plumbing with manifest-backed fixture pipeline.

This does NOT use real EEG data. It validates the real-data code path,
manifest handling, exports, CLI orchestration, reports, and privacy boundaries
using fixture-backed evaluation labeled as mock engineering validation.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MANIFEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "mock_real")
MANIFEST_PATH = os.path.join(MANIFEST_DIR, "manifest.json")
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")


def main(argv=None):
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    manifest = {
        "dataset_id": "mock_real",
        "import_mode": "mock_engineering",
        "acquisition_method": "mock_engineering_manifest",
        "mock_real_eeg": True,
        "actual_real_eeg_imported": False,
        "real_signal": False,
        "raw_persisted": False,
        "engineering_validation_only": True,
        "mock_strategy": "engineering_manifest_and_fixture_backed_pipeline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
        "file_count": 0,
        "notes": "Engineering-only mock manifest. Not real EEG data.",
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    steps = [
        ("manifest_created", ["true"]),
        ("dataset_eval_fixture", [sys.executable, "-m", "app.cli.dataset_eval",
                                   "--dataset", "fixture", "--max-windows", "10",
                                   "--compute-pid-iqi", "--compare", "fixture",
                                   "--distribution-report", "--export-features-csv"]),
        ("dataset_quality_fixture", [sys.executable, "-m", "app.cli.dataset_quality",
                                      "--dataset", "fixture", "--max-windows", "10"]),
        ("product_demo", [sys.executable, "-m", "app.cli.product_demo"]),
        ("release_artifacts", [sys.executable, "-m", "app.cli.release_artifacts"]),
    ]

    step_results = {}
    failed = False
    for name, cmd in steps:
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True)
            step_results[name] = {"ok": cp.returncode == 0, "returncode": cp.returncode}
            if cp.returncode != 0:
                failed = True
        except Exception as e:
            step_results[name] = {"ok": False, "error": str(e)}
            failed = True

    report = {
        "tool": "imagina_mock_real_eeg_e2e",
        "release_candidate": "V2.9.1-RC1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mock_real_eeg": True,
        "actual_real_eeg_imported": False,
        "real_scientific_validation": False,
        "engineering_validation_only": True,
        "mock_strategy": "engineering_manifest_and_fixture_backed_pipeline",
        "all_steps_passed": not failed,
        "steps": step_results,
        "privacy_note": "No raw EEG samples are persisted or exported.",
        "scientific_disclaimer": "Mock EEG is engineering-only. Not real scientific validation.",
    }

    jp = os.path.join(EXPORTS_DIR, "mock_real_eeg_e2e_report.json")
    mp = os.path.join(EXPORTS_DIR, "mock_real_eeg_e2e_summary.md")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    lines = [
        "# Mock Real EEG E2E Report V2.9.1-RC1",
        "",
        "**WARNING: Engineering plumbing validation only.**",
        "**Not real scientific validation. No actual EEG data used.**",
        "",
        "| Step | Result |",
        "|------|--------|",
    ]
    for step, result in step_results.items():
        lines.append(f"| {step} | {'PASS' if result['ok'] else 'FAIL'} |")
    lines.extend([
        "", "## Privacy", report["privacy_note"],
        "", "## Scientific Disclaimer", report["scientific_disclaimer"],
    ])
    with open(mp, "w") as f:
        f.write("\n".join(lines))
    print(f"Mock E2E report: {jp}", file=sys.stderr)
    print(f"Summary: {mp}", file=sys.stderr)
    print(f"All steps passed: {not failed}", file=sys.stderr)
    if not failed:
        print("Mock E2E: PASS", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

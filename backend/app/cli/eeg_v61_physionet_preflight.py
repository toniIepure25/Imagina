"""V6.1 PhysioNet Preflight & Verdict CLI.

Preflight mode: load adapter, run corrected metadata preflight per task.
Verdict mode: decide train_allowed status, write scientific verdict.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v61_physionet_preflight")
    p.add_argument("--mode", default="all",
                   choices=["manifest", "preflight", "verdict", "all"])
    p.add_argument("--max-subjects", type=int, default=20)
    p.add_argument("--output-prefix", default="eeg_v61_physionet")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    if args.mode in ("manifest", "all"):
        from app.eeg_datasets.physionet_eegmmi_adapter import export_manifest
        manifest = export_manifest()
        print(f"Manifest: data_available={manifest['data_available']} "
              f"backend={manifest['loader_backend']}", file=sys.stderr)

    if args.mode in ("preflight", "all"):
        from app.eeg_datasets.physionet_eegmmi_adapter import CANDIDATE_TASKS, _check_deps, load_metadata_rows
        from app.eeg_datasets.preflight import evaluate_preflight

        deps = _check_deps()
        rows = load_metadata_rows()
        data_available = len(rows) > 0 and (deps["moabb"] or deps["mne"])

        preflight_results = {}
        if not data_available:
            for task in CANDIDATE_TASKS:
                preflight_results[task["task_name"]] = {
                    "metadata_safe": False,
                    "allowed_to_train_eeg_model": False,
                    "status": "data_unavailable",
                    "nuisance_baselines": {},
                    "combined_nuisance_baseline": None,
                    "dummy_baseline": None,
                    "failure_reasons": ["data_unavailable"],
                    "recommended_status": "data_unavailable",
                }
        else:
            for task in CANDIDATE_TASKS:
                result = evaluate_preflight(rows, task)
                result["recommended_status"] = (
                    "train_allowed" if result.get("allowed_to_train_eeg_model")
                    else "blocked_by_metadata" if result.get("failure_reasons")
                    else "needs_manual_review"
                )
                preflight_results[task["task_name"]] = result
                status = result["recommended_status"]
                safe_str = "SAFE" if result.get("metadata_safe") else "FAIL"
                print(f"  {task['task_name']}: {status} ({safe_str})", file=sys.stderr)

        preflight_json = {**_safety(), "tool": "eeg_v61_physionet_metadata_preflight_results",
                          "generated_at": datetime.now(timezone.utc).isoformat(),
                          "data_available": data_available,
                          "preflight_results": preflight_results}
        with open(os.path.join(EXPORTS, "eeg_v61_physionet_metadata_preflight_results.json"), "w") as f:
            json.dump(preflight_json, f, indent=2, default=str)

    if args.mode in ("verdict", "all"):
        results = None
        rpath = os.path.join(EXPORTS, "eeg_v61_physionet_metadata_preflight_results.json")
        if os.path.exists(rpath):
            with open(rpath) as f:
                results = json.load(f)

        if not results or not results.get("data_available"):
            verdict = "data_unavailable"
            safe_list = "none"
        else:
            safe_tasks = [k for k, v in results.get("preflight_results", {}).items()
                          if v.get("allowed_to_train_eeg_model")]
            verdict = ("metadata_safe_task_found" if safe_tasks
                        else "no_train_allowed_task")
            safe_list = ", ".join(safe_tasks) if safe_tasks else "none"

        scientific_verdict = {
            **_safety(),
            "tool": "eeg_v61_scientific_verdict",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "safe_tasks": safe_list,
            "interpretation": (
                "PhysioNet EEGMMI data is available via MOABB. "
                "Metadata preflight completed. Training is blocked unless "
                "nuisance metadata baselines remain near chance."
                if results and results.get("data_available")
                else "PhysioNet EEGMMI data is NOT available. "
                     "Install MOABB (pip install moabb) to enable data loading."
            ),
            "next_step": (
                "Run feature builder and benchmark for safe_task"
                if safe_list != "none" else
                "Install dependencies and retry: pip install moabb mne"
            ),
        }
        with open(os.path.join(EXPORTS, "eeg_v61_scientific_verdict.json"), "w") as f:
            json.dump(scientific_verdict, f, indent=2, default=str)
        print(f"Verdict: {verdict}", file=sys.stderr)

    # Export corrected preflight protocol
    from app.eeg_datasets.preflight import export_protocol
    export_protocol()

    # Dataset status registry
    registry = {
        **_safety(), "tool": "eeg_v61_dataset_status_registry",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {
            "OpenMIIR": {"status": "negative_control_invalid", "reason": "metadata_confounded"},
            "PhysioNet_EEGMMI": {"status": "preflight_complete",
                                 "verdict": "pending_load"},
            "BNCI_2014_001": {"status": "backup_pending_preflight"},
            "OpenBMI": {"status": "candidate_pending_preflight"},
            "THINGS_EEG": {"status": "perception_only_candidate"},
        },
    }
    with open(os.path.join(EXPORTS, "eeg_v61_dataset_status_registry.json"), "w") as f:
        json.dump(registry, f, indent=2, default=str)

    return 0


if __name__ == "__main__":
    sys.exit(main())

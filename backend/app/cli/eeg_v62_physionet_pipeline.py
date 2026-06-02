"""V6.2 PhysioNet Pipeline — Loader resolution, corrected preflight, train gate, verdict."""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v62_physionet_pipeline")
    p.add_argument("--mode", default="all",
                   choices=["manifest", "loader", "preflight", "gate", "verdict", "all"])
    p.add_argument("--max-subjects", type=int, default=20)
    p.add_argument("--output-prefix", default="eeg_v62_physionet")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _save(data, filename):
    with open(os.path.join(EXPORTS, filename), "w") as f:
        json.dump(data, f, indent=2, default=str)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    if args.mode in ("manifest", "all"):
        from app.eeg_datasets.physionet_eegmmi_adapter import export_manifest
        manifest = export_manifest()
        _save(manifest, "eeg_v62_physionet_adapter_manifest.json")
        print(f"Manifest: data_available={manifest['data_available']} "
              f"backend={manifest['loader_backend']}", file=sys.stderr)

    if args.mode in ("loader", "all"):
        from app.eeg_datasets.physionet_eegmmi_adapter import (
            CANDIDATE_TASKS,
            _check_deps,
            load_metadata_rows,
            validate_task_sample_counts,
        )

        deps = _check_deps()
        loader_report = {
            **_safety(), "tool": "eeg_v62_loader_resolution",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "moabb_available": deps["moabb"],
            "mne_available": deps["mne"],
            "has_physionet_loader": deps["has_physionet_loader"],
            "selected_loader": "moabb" if deps["moabb"] else ("mne" if deps["mne"] else "none"),
            "can_load_metadata": deps["has_physionet_loader"],
            "install_suggestion": ("pip install moabb" if not deps["moabb"] else "none"),
        }
        _save(loader_report, "eeg_v62_loader_resolution.json")

        # Load real metadata
        rows = load_metadata_rows(args.max_subjects)
        data_available = len(rows) > 0

        if data_available:
            summary = {
                **_safety(), "tool": "eeg_v62_physionet_metadata_rows_summary",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "n_rows": len(rows),
                "n_subjects": len(set(r["subject_id"] for r in rows)),
                "loader_backend": loader_report["selected_loader"],
            }
            _save(summary, "eeg_v62_physionet_metadata_rows_summary.json")

            # Task sample counts
            task_counts = {}
            for task in CANDIDATE_TASKS:
                task_counts[task["task_name"]] = validate_task_sample_counts(rows, task)
            _save({**_safety(), "tool": "eeg_v62_physionet_task_sample_counts",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "tasks": task_counts},
                  "eeg_v62_physionet_task_sample_counts.json")
            print(f"Loader: {len(rows)} metadata rows, "
                  f"{len(set(r['subject_id'] for r in rows))} subjects",
                  file=sys.stderr)
        else:
            print("Loader: data_unavailable (MOABB not installed, MNE fallback empty)",
                  file=sys.stderr)
            _save({"status": "data_unavailable", "reason": "no_loader_available"},
                  "eeg_v62_physionet_metadata_rows_summary.json")

    if args.mode in ("preflight", "all"):
        from app.eeg_datasets.physionet_eegmmi_adapter import (
            CANDIDATE_TASKS,
            load_metadata_rows,
        )
        from app.eeg_datasets.preflight import evaluate_preflight

        rows = load_metadata_rows(args.max_subjects)
        if not rows:
            _save({**_safety(), "status": "data_unavailable", "preflight_results": {}},
                  "eeg_v62_physionet_preflight_results.json")
            print("Preflight: data_unavailable", file=sys.stderr)
        else:
            results = {}
            for task in CANDIDATE_TASKS:
                pf = evaluate_preflight(rows, task)
                safe = pf.get("metadata_safe", False)
                comb = pf.get("combined_nuisance_baseline", "?")
                status_str = "SAFE" if safe else "FAIL"
                print(f"  {task['task_name']}: {status_str} comb_nuisance={comb}",
                      file=sys.stderr)
                results[task["task_name"]] = pf

            _save({**_safety(), "tool": "eeg_v62_physionet_preflight_results",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "data_available": True, "preflight_results": results},
                  "eeg_v62_physionet_preflight_results.json")

    if args.mode in ("gate", "all"):
        rpath = os.path.join(EXPORTS, "eeg_v62_physionet_preflight_results.json")
        if not os.path.exists(rpath):
            gate = {**_safety(), "tool": "eeg_v62_train_gate",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "train_allowed": False, "safe_tasks": [], "blocked_tasks": [],
                    "reason": "preflight_not_run",
                    "next_step": "Run preflight first"}
            _save(gate, "eeg_v62_train_gate.json")
        else:
            with open(rpath) as f:
                pr = json.load(f)
            safe = [k for k, v in pr.get("preflight_results", {}).items()
                    if v.get("metadata_safe")]
            blocked = [k for k, v in pr.get("preflight_results", {}).items()
                       if not v.get("metadata_safe")]
            train_allowed = len(safe) > 0
            gate = {**_safety(), "tool": "eeg_v62_train_gate",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "train_allowed": train_allowed, "safe_tasks": safe,
                    "blocked_tasks": blocked,
                    "reason": ("At least one task passed preflight" if train_allowed
                               else "All tasks blocked by metadata preflight"),
                    "next_step": ("Run epoch builder for a safe task" if train_allowed
                                  else "Fix metadata confounds before training")}
            _save(gate, "eeg_v62_train_gate.json")
            print(f"Train gate: allowed={train_allowed} safe={len(safe)} blocked={len(blocked)}",
                  file=sys.stderr)

    if args.mode in ("verdict", "all"):
        loader = None
        gate_data = None
        lp = os.path.join(EXPORTS, "eeg_v62_loader_resolution.json")
        gp = os.path.join(EXPORTS, "eeg_v62_train_gate.json")
        if os.path.exists(lp):
            with open(lp) as f:
                loader = json.load(f)
        if os.path.exists(gp):
            with open(gp) as f:
                gate_data = json.load(f)

        can_load = (loader or {}).get("can_load_metadata", False)
        train_ok = (gate_data or {}).get("train_allowed", False)

        if not can_load:
            verdict_str = "data_unavailable"
        elif not train_ok:
            verdict_str = "metadata_preflight_failed"
        else:
            verdict_str = "train_allowed_no_benchmark_yet"

        verdict = {
            **_safety(), "tool": "eeg_v62_scientific_verdict",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict_str,
            "interpretation": (
                "Data unavailable — install MOABB (pip install moabb) to enable PhysioNet EEGMMI loading."
                if not can_load else
                "Preflight failed — nuisance metadata predicts the label. Training blocked."
                if not train_ok else
                "Preflight passed — at least one task is safe for training. Run epoch builder next."
            ),
        }
        _save(verdict, "eeg_v62_scientific_verdict.json")

        # Dataset status registry update
        registry = {
            **_safety(), "tool": "eeg_v62_dataset_status_registry",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": {
                "OpenMIIR": {"status": "negative_control_invalid",
                             "reason": "metadata_confounded"},
                "PhysioNet_EEGMMI": {"status": verdict_str,
                                     "can_load": can_load,
                                     "train_allowed": train_ok},
                "BNCI_2014_001": {"status": "backup_pending_preflight"},
                "OpenBMI": {"status": "candidate_pending_preflight"},
                "THINGS_EEG": {"status": "perception_only_candidate"},
            },
        }
        _save(registry, "eeg_v62_dataset_status_registry.json")
        print(f"Verdict: {verdict_str}", file=sys.stderr)

    # Export preflight protocol
    from app.eeg_datasets.preflight import export_protocol
    export_protocol()

    return 0


if __name__ == "__main__":
    sys.exit(main())

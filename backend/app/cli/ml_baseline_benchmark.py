"""ML baseline benchmark for EEG feature-based classification."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.ml_baseline_benchmark")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--task", default="auto")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--max-windows-per-subject", type=int, default=200)
    p.add_argument("--output-prefix", default="openmiir_ml_baseline")
    return p


def _extract(subject_windows, label_fn):
    x_vals, y_vals, s_vals = [], [], []
    for subj, windows in subject_windows.items():
        from app.services.feature_engine import FeatureEngine
        for w in windows:
            fv = FeatureEngine().process_eeg_window(w)
            x_vals.append([
                fv.theta_power, fv.alpha_power, fv.beta_power,
                fv.theta_beta_ratio, fv.alpha_stability, fv.signal_quality,
                fv.blink_score or 0, fv.muscle_score or 0,
                fv.drift_score or 0, fv.clipping_score or 0,
                fv.missing_data_ratio or 0,
            ])
            y_vals.append(label_fn(subj, fv))
            s_vals.append(subj)
    return np.array(x_vals), np.array(y_vals), np.array(s_vals)


def _run_models(x_vals, y_vals, s_vals):
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
    from sklearn.model_selection import LeaveOneGroupOut
    from sklearn.preprocessing import StandardScaler

    x_vals = StandardScaler().fit_transform(x_vals)
    models = {
        "DummyClassifier": DummyClassifier(strategy="stratified", random_state=42),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1),
    }
    results = {}
    cv = LeaveOneGroupOut()
    for name, model in models.items():
        yt_all, yp_all = [], []
        try:
            for ti, vi in cv.split(x_vals, y_vals, s_vals):
                model.fit(x_vals[ti], y_vals[ti])
                yp_all.extend(model.predict(x_vals[vi]))
                yt_all.extend(y_vals[vi])
        except Exception:
            continue
        yt_a = np.array(yt_all)
        yp_a = np.array(yp_all)
        results[name] = {
            "accuracy": round(accuracy_score(yt_a, yp_a), 4),
            "balanced_accuracy": round(balanced_accuracy_score(yt_a, yp_a), 4),
            "f1_weighted": round(f1_score(yt_a, yp_a, average="weighted"), 4),
        }
    return results


def main(argv=None):
    args = build_parser().parse_args(argv)
    mp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "manifest.json",
    )
    if not os.path.exists(mp):
        print(f"No manifest for '{args.dataset}'", file=sys.stderr)
        return 1

    from app.datasets.loaders import safe_read_raw
    from app.datasets.windowing import windows_from_raw
    with open(mp) as f:
        files = json.load(f).get("files", [])[: args.max_subjects]
    subj_win = {}
    for fif in files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            raw = safe_read_raw(fif)
            raw.crop(tmax=min(raw.n_times / raw.info["sfreq"], 30))
            subj_win[subj] = windows_from_raw(raw, max_windows=args.max_windows_per_subject)
        except Exception:
            pass
    if len(subj_win) < 2:
        print("Need >=2 subjects", file=sys.stderr)
        return 1

    benchmarks = {}
    id_map = {s: i for i, s in enumerate(subj_win.keys())}
    xv, yv, sv = _extract(subj_win, lambda s, fv: id_map[s])
    if len(set(yv)) >= 2:
        benchmarks["subject_classification"] = {
            "task_type": "sanity_check",
            "models": _run_models(xv, yv, sv),
        }

    xv2, yv2, sv2 = _extract(subj_win, lambda s, fv: 1 if fv.signal_quality > 0.5 else 0)
    if len(set(yv2)) >= 2:
        benchmarks["signal_quality_high_vs_low"] = {
            "task_type": "sanity_check",
            "models": _run_models(xv2, yv2, sv2),
        }

    report = {
        "tool": "imagina_ml_baseline_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_candidate": "V3.3",
        "dataset": args.dataset,
        "subjects_used": len(subj_win),
        "condition_labels_available": False,
        "benchmarks": benchmarks,
        "disclaimer": (
            "ML benchmark for engineering evaluation only. "
            "Not a validated imagery classifier or clinical tool."
        ),
    }

    prefix = args.output_prefix
    jp = _exports_path(f"{prefix}_benchmark.json")
    rp = _exports_path(f"{prefix}_benchmark.md")
    cp = _exports_path(f"{prefix}_features.csv")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(cp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "alpha_power", "theta_power", "beta_power", "signal_quality"])
        w.writeheader()
        for subj, ws in subj_win.items():
            from app.services.feature_engine import FeatureEngine
            for wi in ws:
                fv = FeatureEngine().process_eeg_window(wi)
                w.writerow({
                    "subject": subj, "alpha_power": fv.alpha_power,
                    "theta_power": fv.theta_power, "beta_power": fv.beta_power,
                    "signal_quality": fv.signal_quality,
                })
    lines = [
        "# IMAGINA ML Baseline Benchmark",
        f"**Dataset**: {args.dataset} | **Subjects**: {len(subj_win)}",
        "",
        "## Condition Labels: NOT AVAILABLE (sanity-check tasks only)",
    ]
    for task, bm in benchmarks.items():
        lines.extend([f"### {task}", "", "| Model | Acc | BAcc | F1 |", "|---|---|---|---|"])
        for mname, metrics in bm["models"].items():
            lines.append(
                f"| {mname} | {metrics['accuracy']:.4f} | "
                f"{metrics['balanced_accuracy']:.4f} | {metrics['f1_weighted']:.4f} |"
            )
        lines.append("")
    with open(rp, "w") as f:
        f.write("\n".join(lines))
    print(f"ML benchmark: {jp}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Imagery Quality Index v2 CLI — compute per-subject and cohort IQI v2 scores."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _figures_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "figures")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.imagery_quality_v2")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--max-windows-per-subject", type=int, default=200)
    p.add_argument("--output-prefix", default="openmiir_iqi_v2")
    return p


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
    from app.services.feature_engine import FeatureEngine
    from app.services.imagery_quality_v2 import compute_iqi_v2

    with open(mp) as f:
        files = json.load(f).get("files", [])[: args.max_subjects]
    if not files:
        print("No files", file=sys.stderr)
        return 1

    engine = FeatureEngine()
    subject_results = []
    all_scores = []
    all_components = {}

    for fif in files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            raw = safe_read_raw(fif)
            dur = min(raw.n_times / raw.info["sfreq"], 30)
            raw.crop(tmax=dur)
            windows = windows_from_raw(raw, max_windows=args.max_windows_per_subject)
            fvs = [engine.process_eeg_window(w) for w in windows]
            iqi = compute_iqi_v2(fvs)
            sr = iqi.copy()
            sr["subject"] = subj
            sr["n_windows"] = len(fvs)
            sr["sampling_rate_hz"] = float(raw.info["sfreq"])
            sr["channel_count"] = raw.info["nchan"]
            subject_results.append(sr)
            all_scores.append(iqi["final_score"])
            for c in iqi["components"]:
                all_components.setdefault(c["name"], []).append(c["score"])
        except Exception:
            pass

    if not subject_results:
        print("No subjects processed", file=sys.stderr)
        return 1

    cohort = {
        "n_subjects": len(subject_results),
        "iqi_mean": round(float(np.mean(all_scores)), 4),
        "iqi_std": round(float(np.std(all_scores)), 4) if len(all_scores) > 1 else 0,
        "iqi_min": round(float(np.min(all_scores)), 4),
        "iqi_max": round(float(np.max(all_scores)), 4),
        "component_means": {k: round(float(np.mean(v)), 4) for k, v in all_components.items()},
    }

    report = {
        "tool": "imagina_imagery_quality_v2",
        "release_candidate": "V3.6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric_name": "ImageryQualityIndex",
        "metric_version": "v2.0",
        "dataset": args.dataset,
        "cohort": cohort,
        "subject_results": [{"subject": r["subject"], "iqi": r["final_score"], "confidence": r["confidence"],
                             "n_windows": r["n_windows"], "components": r["components"]} for r in subject_results],
        "limitations": [
            "Experimental EEG-derived proxy metric — not clinical",
            "Not a validated imagery measure",
            "Requires controlled experiments with labels for validation",
            "Does not decode thoughts or read minds",
        ],
        "allowed_claims": subject_results[0]["allowed_claims"],
        "forbidden_claims": subject_results[0]["forbidden_claims"],
    }

    prefix = args.output_prefix
    jp = _exports_path(f"{prefix}.json")
    rp = _exports_path(f"{prefix}.md")
    cp = _exports_path(f"{prefix}_subjects.csv")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(cp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "iqi_v2", "confidence", "n_windows"])
        w.writeheader()
        for r in subject_results:
            payload = {"subject": r["subject"], "iqi_v2": r["final_score"],
                       "confidence": r["confidence"], "n_windows": r["n_windows"]}
            w.writerow(payload)

    lines = [
        "# Imagery Quality Index v2",
        f"**Metric**: {report['metric_name']} {report['metric_version']}",
        f"**Subjects**: {cohort['n_subjects']} | **IQI mean**: {cohort['iqi_mean']:.4f}",
        "",
        "## Cohort Summary",
        f"- Mean: {cohort['iqi_mean']:.4f}",
        f"- Std: {cohort['iqi_std']:.4f}",
        f"- Range: [{cohort['iqi_min']:.4f}, {cohort['iqi_max']:.4f}]",
        "",
        "## Subject IQI v2",
        "| Subject | IQI v2 | Confidence | Windows |",
        "|---------|--------|-----------|---------|",
    ]
    for r in subject_results:
        lines.append(f"| {r['subject']} | {r['final_score']:.4f} | {r['confidence']:.4f} | {r['n_windows']} |")
    lines.extend([
        "",
        "## Component Means",
        "| Component | Mean Score |",
        "|-----------|-----------|",
    ])
    for k, v in cohort["component_means"].items():
        lines.append(f"| {k} | {v:.4f} |")
    lines.extend([
        "",
        "## Limitations",
    ])
    for lim in report["limitations"]:
        lines.append(f"- {lim}")
    with open(rp, "w") as f:
        f.write("\n".join(lines))

    # Figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.hist(all_scores, bins=min(8, len(all_scores)), alpha=0.7, color="steelblue")
        ax.set_title("IQI v2 Distribution Across Subjects")
        ax.set_xlabel("IQI v2 Score")
        fig.savefig(_figures_path(f"{prefix}_distribution.png"), dpi=100)
        plt.close(fig)

        fig2, ax2 = plt.subplots(figsize=(10, 4))
        comp_names = list(cohort["component_means"].keys())
        comp_vals = list(cohort["component_means"].values())
        ax2.bar(comp_names, comp_vals, alpha=0.7, color="darkcyan")
        ax2.set_title("IQI v2 Component Contribution")
        ax2.set_ylabel("Mean Score")
        plt.xticks(rotation=30, ha="right", fontsize=8)
        fig2.savefig(_figures_path(f"{prefix}_components.png"), dpi=100)
        plt.close(fig2)
    except Exception:
        pass

    print(f"IQI v2: {jp}", file=sys.stderr)
    print(f"  Subjects: {cohort['n_subjects']} | IQI mean: {cohort['iqi_mean']:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

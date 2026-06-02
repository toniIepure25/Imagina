"""Cross-subject OpenMIIR evaluation — per-subject bandpower, quality, and comparison."""

import csv
import json
import os
import sys
from datetime import datetime, timezone


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def main(argv=None):
    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir", "manifest.json"
    )
    if not os.path.exists(manifest_path):
        print("No OpenMIIR manifest found. Import real EEG first.", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        manifest = json.load(f)
    files = manifest.get("files", [])
    if not files:
        print("No FIF files in manifest.", file=sys.stderr)
        return 1

    from app.datasets.loaders import safe_read_raw, summarize_raw
    from app.datasets.windowing import windows_from_raw
    from app.services.feature_engine import FeatureEngine
    from app.services.signal_quality import evaluate_signal_quality

    engine = FeatureEngine()
    results = []
    errors = []

    for fif_path in files:
        subject = os.path.splitext(os.path.basename(fif_path))[0]
        try:
            raw = safe_read_raw(fif_path)
            meta = summarize_raw(raw)
            windows = windows_from_raw(raw, max_windows=20, dataset_id=subject, provider_id="cross_subject")
            fvs = [engine.process_eeg_window(w) for w in windows]
            quality = evaluate_signal_quality(fvs)

            alpha_vals = [fv.alpha_power for fv in fvs]
            theta_vals = [fv.theta_power for fv in fvs]
            beta_vals = [fv.beta_power for fv in fvs]
            sq_vals = [fv.signal_quality for fv in fvs]
            mdr_vals = [fv.missing_data_ratio or 0 for fv in fvs]

            results.append({
                "subject": subject,
                "windows": len(fvs),
                "sampling_rate_hz": meta["sampling_rate_hz"],
                "channel_count": meta["channel_count"],
                "duration_seconds": meta["duration_seconds"],
                "alpha_mean": round(sum(alpha_vals) / len(alpha_vals), 4) if alpha_vals else 0,
                "theta_mean": round(sum(theta_vals) / len(theta_vals), 4) if theta_vals else 0,
                "beta_mean": round(sum(beta_vals) / len(beta_vals), 4) if beta_vals else 0,
                "theta_beta_ratio": round(
                    (sum(theta_vals) / len(theta_vals)) / max(sum(beta_vals) / len(beta_vals), 0.01), 4
                ) if beta_vals and theta_vals else 0,
                "signal_quality_mean": round(sum(sq_vals) / len(sq_vals), 4),
                "signal_quality_min": round(min(sq_vals), 4),
                "signal_quality_max": round(max(sq_vals), 4),
                "missing_data_mean": round(sum(mdr_vals) / len(mdr_vals), 4) if mdr_vals else 0,
                "quality_score": quality["quality_score"],
                "quality_warnings": quality["warnings"],
            })
        except Exception as e:
            errors.append(f"{subject}: {e}")

    if not results:
        print("No subjects processed.", file=sys.stderr)
        return 1

    # Aggregate across subjects
    alphas = [r["alpha_mean"] for r in results]
    thetas = [r["theta_mean"] for r in results]
    betas = [r["beta_mean"] for r in results]
    sqs = [r["signal_quality_mean"] for r in results]

    report = {
        "tool": "imagina_cross_subject_eval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "OpenMIIR",
        "subjects_processed": len(results),
        "subjects_failed": len(errors),
        "subject_results": results,
        "cross_subject_aggregate": {
            "alpha_mean": round(sum(alphas) / len(alphas), 4),
            "alpha_std": round(_std(alphas), 4),
            "theta_mean": round(sum(thetas) / len(thetas), 4),
            "theta_std": round(_std(thetas), 4),
            "beta_mean": round(sum(betas) / len(betas), 4),
            "beta_std": round(_std(betas), 4),
            "signal_quality_mean": round(sum(sqs) / len(sqs), 4),
            "signal_quality_std": round(_std(sqs), 4),
        },
        "errors": errors,
        "disclaimer": (
            "Experimental proxy features from real EEG. Engineering evaluation only. "
            "Not clinical validation. Does not decode thoughts or read minds."
        ),
    }

    jp = _exports_path("cross_subject_eval.json")
    mp = _exports_path("cross_subject_eval.md")
    cp = _exports_path("cross_subject_eval.csv")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # CSV
    csv_headers = [
        "subject", "windows", "alpha_mean", "theta_mean", "beta_mean",
        "theta_beta_ratio", "signal_quality_mean", "quality_score",
    ]
    with open(cp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in csv_headers})

    # Markdown
    lines = [
        "# OpenMIIR Cross-Subject Evaluation",
        "",
        f"**Subjects**: {len(results)} processed, {len(errors)} failed",
        "",
        "## Per-Subject Results",
        "",
        "| Subject | Windows | Alpha | Theta | Beta | T/B Ratio | Signal Q | Quality |",
        "|---------|---------|-------|-------|------|-----------|----------|---------|",
    ]
    for r in results:
        lines.append(
            f"| {r['subject']} | {r['windows']} | {r['alpha_mean']:.4f} | "
            f"{r['theta_mean']:.4f} | {r['beta_mean']:.4f} | "
            f"{r['theta_beta_ratio']:.4f} | {r['signal_quality_mean']:.4f} | "
            f"{r['quality_score']:.4f} |"
        )
    agg = report["cross_subject_aggregate"]
    lines.extend([
        "",
        "## Cross-Subject Aggregate",
        "",
        "| Metric | Mean | Std |",
        "|--------|------|-----|",
        f"| Alpha | {agg['alpha_mean']:.4f} | {agg['alpha_std']:.4f} |",
        f"| Theta | {agg['theta_mean']:.4f} | {agg['theta_std']:.4f} |",
        f"| Beta | {agg['beta_mean']:.4f} | {agg['beta_std']:.4f} |",
        f"| Signal quality | {agg['signal_quality_mean']:.4f} | {agg['signal_quality_std']:.4f} |",
        "",
        "## Disclaimer",
        report["disclaimer"],
    ])
    with open(mp, "w") as f:
        f.write("\n".join(lines))

    print(
        f"Cross-subject eval: {jp}", file=sys.stderr,
    )
    print(
        f"  Subjects: {len(results)} | "
        f"Aggregate alpha: {agg['alpha_mean']:.4f} | "
        f"SQ: {agg['signal_quality_mean']:.4f}",
        file=sys.stderr,
    )
    return 0


def _std(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


if __name__ == "__main__":
    sys.exit(main())

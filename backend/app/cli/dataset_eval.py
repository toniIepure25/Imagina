"""Dataset evaluation CLI — validates FeatureEngine on dataset/fixture windows."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from app.datasets.loaders import load_windows
from app.services.feature_engine import FeatureEngine
from app.services.pid_iqi_engine import PIDIQIEngine
from app.services.state_estimator import StateEstimator


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m app.cli.dataset_eval",
        description="Evaluate pipeline on dataset windows.",
    )
    p.add_argument("--dataset", default="fixture", help="Dataset ID (default: fixture)")
    p.add_argument("--max-windows", type=int, default=50)
    p.add_argument("--output", default=None, help="Output JSON path")
    p.add_argument("--compute-pid-iqi", action="store_true", help="Also compute PID/IQI proxies")
    p.add_argument("--fallback", default=None, help="Fallback dataset ID if primary is unavailable")
    p.add_argument(
        "--compare", default=None,
        help="Compare primary dataset against this dataset (exploratory only)",
    )
    p.add_argument("--distribution-report", action="store_true", help="Generate distribution statistics JSON")
    p.add_argument(
        "--export-features-csv", action="store_true",
        help="Export FeatureVector rows as CSV (no raw samples)",
    )
    p.add_argument("--real-mode", action="store_true", help="Require real EEG manifest; fail if missing")
    return p


def _compute_report(windows, args, requested_ds, actual_ds, fallback_used, fallback_reason):
    engine = FeatureEngine()
    fvs = []
    errors = []
    for i, w in enumerate(windows):
        try:
            fv = engine.process_eeg_window(w)
            fvs.append(fv)
        except Exception as e:
            errors.append(f"Window {i} failed: {e}")

    base: dict = {
        "tool": "imagina_dataset_eval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_dataset": requested_ds,
        "actual_dataset": actual_ds,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "dataset_status": "real_downloaded" if not fallback_used else "fixture_fallback",
        "windows_loaded": len(windows),
        "windows_valid": len(fvs),
        "real_signal": fvs[0].real_signal if fvs else False,
        "errors": errors,
        "disclaimer": (
            "This evaluation uses experimental proxy features. "
            "It does not decode thoughts, diagnose conditions, or provide clinical validation."
        ),
    }

    if not fvs:
        return {**base, "error": "No valid FeatureVectors produced."}

    sq = [fv.signal_quality for fv in fvs]
    mdr = [fv.missing_data_ratio or 0 for fv in fvs]
    alpha = [fv.alpha_power for fv in fvs]
    theta = [fv.theta_power for fv in fvs]
    beta = [fv.beta_power for fv in fvs]
    blink = [fv.blink_score or 0 for fv in fvs]
    muscle = [fv.muscle_score or 0 for fv in fvs]
    drift = [fv.drift_score or 0 for fv in fvs]
    clip = [fv.clipping_score or 0 for fv in fvs]

    base.update({
        "signal_quality": {
            "mean": round(sum(sq) / len(sq), 4),
            "min": round(min(sq), 4),
            "max": round(max(sq), 4),
        },
        "missing_data_ratio": {
            "mean": round(sum(mdr) / len(mdr), 4),
            "max": round(max(mdr), 4),
        },
        "bandpower": {
            "alpha_mean": round(sum(alpha) / len(alpha), 4),
            "theta_mean": round(sum(theta) / len(theta), 4),
            "beta_mean": round(sum(beta) / len(beta), 4),
        },
        "artifacts": {
            "blink_mean": round(sum(blink) / len(blink), 4),
            "muscle_mean": round(sum(muscle) / len(muscle), 4),
            "drift_mean": round(sum(drift) / len(drift), 4),
            "clipping_mean": round(sum(clip) / len(clip), 4),
        },
    })

    if args.compute_pid_iqi:
        pid_iqi = PIDIQIEngine()
        state_est = StateEstimator()
        pid_vals = []
        iqi_vals = []
        for fv in fvs[:30]:
            try:
                state = state_est.estimate("eval", fv, None, {}, 0)
                pid_est, iqi_est = pid_iqi.compute("eval", state, fv, 0)
                pid_vals.append(pid_est.pid)
                iqi_vals.append(iqi_est.iqi)
            except Exception:
                pass
        if pid_vals:
            base["pid_iqi"] = {
                "pid_mean": round(sum(pid_vals) / len(pid_vals), 4),
                "iqi_mean": round(sum(iqi_vals) / len(iqi_vals), 4),
                "windows_evaluated": len(pid_vals),
            }

    return base


def evaluate(args: argparse.Namespace) -> dict:
    if getattr(args, "real_mode", False):
        from app.datasets.manifest import read_manifest
        m = read_manifest(args.dataset)
        if m is None or not m.get("real_signal"):
            raise RuntimeError(
                f"Real mode requested but no real EEG manifest is available for '{args.dataset}'. "
                "Import a real EEG file first using import-local or real_data_wizard."
            )

    requested_ds = args.dataset
    actual_ds = requested_ds
    fallback_used = False
    fallback_reason = None

    try:
        windows = load_windows(requested_ds, max_windows=args.max_windows)
        return _compute_report(windows, args, requested_ds, actual_ds, fallback_used, fallback_reason)
    except Exception as e:
        if not args.fallback:
            raise
        fallback_used = True
        fallback_reason = f"Dataset '{requested_ds}' unavailable: {e}"
        actual_ds = args.fallback
        windows = load_windows(actual_ds, max_windows=args.max_windows)
        return _compute_report(windows, args, requested_ds, actual_ds, fallback_used, fallback_reason)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = evaluate(args)
    except Exception as e:
        print(f"Evaluation failed: {e}", file=sys.stderr)
        return 1

    output_path = args.output or os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "exports",
        f"dataset_eval_{args.dataset}.json",
    )
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Evaluation written to {output_path}", file=sys.stderr)
    print(f"  Windows: {report['windows_valid']}/{report['windows_loaded']} valid", file=sys.stderr)
    if "signal_quality" in report:
        print(f"  Signal quality: mean={report['signal_quality']['mean']:.3f}", file=sys.stderr)
    if report.get("fallback_used"):
        print(f"  Note: Fell back to '{report['actual_dataset']}' because {report['fallback_reason']}", file=sys.stderr)
    if report.get("errors"):
        return 1

    if args.distribution_report:
        _write_distribution(report, args, output_path)
    if args.export_features_csv:
        _export_features_csv(args, output_path, report.get("actual_dataset"))

    if args.compare:
        try:
            comp_args = argparse.Namespace(
                dataset=args.compare, max_windows=args.max_windows,
                compute_pid_iqi=args.compute_pid_iqi, output=None, fallback=None, compare=None,
            )
            comp_report = evaluate(comp_args)
            comp_path = os.path.join(os.path.dirname(output_path), f"dataset_eval_{args.compare}_compare.json")
            with open(comp_path, "w") as f:
                json.dump(comp_report, f, indent=2, default=str)
            diff = {
                "primary_dataset": report["actual_dataset"],
                "comparison_dataset": comp_report["actual_dataset"],
                "note": "Exploratory comparison — not scientific validation.",
                "signal_quality_diff": round(
                    report.get("signal_quality", {}).get("mean", 0) -
                    comp_report.get("signal_quality", {}).get("mean", 0), 4
                ),
                "alpha_mean_diff": round(
                    report.get("bandpower", {}).get("alpha_mean", 0) -
                    comp_report.get("bandpower", {}).get("alpha_mean", 0), 4
                ),
                "beta_mean_diff": round(
                    report.get("bandpower", {}).get("beta_mean", 0) -
                    comp_report.get("bandpower", {}).get("beta_mean", 0), 4
                ),
                "theta_mean_diff": round(
                    report.get("bandpower", {}).get("theta_mean", 0) -
                    comp_report.get("bandpower", {}).get("theta_mean", 0), 4
                ),
            }
            diff_fname = f"dataset_eval_compare_{args.dataset}_vs_{args.compare}.json"
            diff_path = os.path.join(os.path.dirname(output_path), diff_fname)
            with open(diff_path, "w") as f:
                json.dump(diff, f, indent=2, default=str)
            print(f"Comparison written to {diff_path}", file=sys.stderr)
            for k, v in diff.items():
                if k.endswith("_diff"):
                    print(f"  {k}: {v}", file=sys.stderr)
        except Exception as e:
            print(f"Comparison failed: {e}", file=sys.stderr)
    return 0


def _write_distribution(report, args, output_path):
    sq_mean = report.get("signal_quality", {}).get("mean", 0)
    bp = report.get("bandpower", {})
    art = report.get("artifacts", {})
    dist = {
        "tool": "imagina_dataset_distribution",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": report["actual_dataset"],
        "windows_loaded": report["windows_loaded"],
        "windows_valid": report["windows_valid"],
        "signal_quality": {
            "mean": sq_mean,
            "min": report.get("signal_quality", {}).get("min", 0),
            "max": report.get("signal_quality", {}).get("max", 0),
        },
        "bandpower": {
            "alpha_mean": bp.get("alpha_mean", 0),
            "beta_mean": bp.get("beta_mean", 0),
            "theta_mean": bp.get("theta_mean", 0),
        },
        "artifacts": {
            "blink_mean": art.get("blink_mean", 0),
            "muscle_mean": art.get("muscle_mean", 0),
            "drift_mean": art.get("drift_mean", 0),
            "clipping_mean": art.get("clipping_mean", 0),
        },
        "missing_data_ratio": report.get("missing_data_ratio", {}),
        "warning_flags": [w for w in ["low_signal_quality"] if sq_mean < 0.4],
        "disclaimer": report.get("disclaimer", ""),
    }
    dist_path = os.path.join(os.path.dirname(output_path), f"dataset_distribution_{args.dataset}.json")
    with open(dist_path, "w") as f:
        json.dump(dist, f, indent=2, default=str)
    print(f"Distribution written to {dist_path}", file=sys.stderr)


def _export_features_csv(args, output_path, actual_dataset=None):
    import csv

    from app.datasets.loaders import load_windows
    from app.services.feature_engine import FeatureEngine
    engine = FeatureEngine()
    ds = actual_dataset or args.dataset
    windows = load_windows(ds, max_windows=args.max_windows)
    csv_path = os.path.join(os.path.dirname(output_path), f"dataset_features_{ds}.csv")
    headers = [
        "window_index", "theta_power", "alpha_power", "beta_power", "theta_beta_ratio",
        "alpha_stability", "signal_quality", "blink_score", "muscle_score", "drift_score",
        "clipping_score", "missing_data_ratio", "real_signal",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for i, w in enumerate(windows):
            try:
                fv = engine.process_eeg_window(w)
                row = fv.model_dump(mode="json")
                row["window_index"] = i
                writer.writerow(row)
            except Exception:
                pass
    print(f"Features CSV written to {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())

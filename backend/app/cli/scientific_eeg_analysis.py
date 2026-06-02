"""Scientific EEG analysis layer — MNE preprocessing, PSD, bandpower, and reporting."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _figures_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "figures")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.scientific_eeg_analysis")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--max-duration-sec", type=float, default=120.0)
    p.add_argument("--notch", type=float, default=50.0)
    p.add_argument("--bandpass-low", type=float, default=1.0)
    p.add_argument("--bandpass-high", type=float, default=40.0)
    p.add_argument("--output-prefix", default="openmiir_scientific")
    p.add_argument("--no-plots", action="store_true")
    return p


def compute_bandpower(raw, sfreq):
    import numpy as np
    from scipy.signal import welch as scipy_welch
    data = raw.get_data()
    chs = min(data.shape[0], 8)
    psds = []
    for ch in range(chs):
        f, pxx = scipy_welch(data[ch], fs=sfreq, nperseg=min(1024, data.shape[1] // 2), detrend="linear")
        psds.append(pxx)
    avg_psd = np.mean(psds, axis=0)
    bands = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
    result = {}
    total = np.trapezoid(avg_psd, f)
    for name, (lo, hi) in bands.items():
        mask = (f >= lo) & (f <= hi)
        if mask.any():
            result[name] = float(np.trapezoid(avg_psd[mask], f[mask]) / max(total, 1e-9))
        else:
            result[name] = 0.0
    result["alpha_theta_ratio"] = result.get("alpha", 0) / max(result.get("theta", 0.01), 0.01)
    result["beta_alpha_ratio"] = result.get("beta", 0) / max(result.get("alpha", 0.01), 0.01)
    result["signal_quality"] = float(result.get("alpha", 0.3) * 0.6 + (1 - min(result.get("beta", 1), 1)) * 0.4)
    return result, f, avg_psd


def main(argv=None):
    args = build_parser().parse_args(argv)
    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "manifest.json",
    )
    if not os.path.exists(manifest_path):
        print(f"No manifest for dataset '{args.dataset}'.", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        manifest = json.load(f)
    files = manifest.get("files", [])[: args.max_subjects]
    if not files:
        print("No files in manifest.", file=sys.stderr)
        return 1

    import numpy as np

    results = []
    errors = []
    all_psd_curves = {}

    for fif in files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            dur = min(raw.n_times / raw.info["sfreq"], args.max_duration_sec)
            raw.crop(tmax=dur)
            raw.load_data()
            if args.notch:
                raw.notch_filter(args.notch, verbose=False)
            raw.filter(args.bandpass_low, args.bandpass_high, verbose=False)
            bp, freqs, psd_curve = compute_bandpower(raw, raw.info["sfreq"])
            n_ch = raw.info["nchan"]
            results.append({
                "subject": subj,
                "duration_seconds": round(dur, 2),
                "sampling_rate_hz": float(raw.info["sfreq"]),
                "channel_count": n_ch,
                "delta": round(bp["delta"], 4),
                "theta": round(bp["theta"], 4),
                "alpha": round(bp["alpha"], 4),
                "beta": round(bp["beta"], 4),
                "alpha_theta_ratio": round(bp["alpha_theta_ratio"], 4),
                "beta_alpha_ratio": round(bp["beta_alpha_ratio"], 4),
                "signal_quality": round(bp["signal_quality"], 4),
            })
            all_psd_curves[subj] = {"freqs": freqs.tolist(), "psd": psd_curve.tolist()}
        except Exception as e:
            errors.append(f"{subj}: {e}")

    if not results:
        print("No subjects processed.", file=sys.stderr)
        return 1

    bands = ["delta", "theta", "alpha", "beta", "alpha_theta_ratio", "beta_alpha_ratio", "signal_quality"]
    aggregate = {}
    for b in bands:
        vals = [r[b] for r in results]
        aggregate[b] = {
            "mean": round(np.mean(vals), 4),
            "std": round(np.std(vals) if len(vals) > 1 else 0, 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
        }

    report = {
        "tool": "imagina_scientific_eeg_analysis",
        "release_candidate": "V3.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "subjects_processed": len(results),
        "subjects_failed": len(errors),
        "preprocessing": {
            "notch_hz": args.notch,
            "bandpass_low_hz": args.bandpass_low,
            "bandpass_high_hz": args.bandpass_high,
            "max_duration_sec": args.max_duration_sec,
        },
        "subject_results": results,
        "aggregate": aggregate,
        "errors": errors,
        "disclaimer": (
            "MNE-preprocessed EEG bandpower analysis. Engineering/scientific "
            "evaluation of experimental proxy features. Not clinical validation. "
            "Does not decode thoughts or read minds."
        ),
    }

    prefix = args.output_prefix
    jp = _exports_path(f"{prefix}_analysis.json")
    mp = _exports_path(f"{prefix}_analysis.md")
    bp_csv = _exports_path(f"{prefix}_subject_bandpower.csv")
    sq_csv = _exports_path(f"{prefix}_subject_quality.csv")

    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Bandpower CSV
    bp_cols = ["subject", "delta", "theta", "alpha", "beta", "alpha_theta_ratio", "beta_alpha_ratio"]
    with open(bp_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bp_cols)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in bp_cols})

    # Quality CSV
    sq_cols = ["subject", "signal_quality", "channel_count", "duration_seconds"]
    with open(sq_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sq_cols)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in sq_cols})

    # Markdown
    lines = [
        "# IMAGINA Scientific EEG Analysis",
        f"**Release**: V3.1 | **Dataset**: {args.dataset}",
        f"**Subjects**: {len(results)} | **Failed**: {len(errors)}",
        "",
        "## Preprocessing",
        f"- Notch: {args.notch} Hz | Bandpass: {args.bandpass_low}-{args.bandpass_high} Hz",
        f"- Max duration: {args.max_duration_sec}s",
        "",
        "## Subject-Level Bandpower",
        "",
        "| Subject | Delta | Theta | Alpha | Beta | A/T | B/A | SQ |",
        "|---------|-------|-------|-------|------|-----|-----|-----|",
    ]
    for r in results:
        lines.append(
            f"| {r['subject']} | {r['delta']:.4f} | {r['theta']:.4f} | "
            f"{r['alpha']:.4f} | {r['beta']:.4f} | "
            f"{r['alpha_theta_ratio']:.4f} | {r['beta_alpha_ratio']:.4f} | "
            f"{r['signal_quality']:.4f} |"
        )
    lines.extend([
        "",
        "## Aggregate Statistics",
        "",
        "| Band | Mean | Std | Min | Max |",
        "|------|------|-----|-----|-----|",
    ])
    for b in bands:
        a = aggregate[b]
        lines.append(f"| {b} | {a['mean']:.4f} | {a['std']:.4f} | {a['min']:.4f} | {a['max']:.4f} |")
    lines.extend([
        "",
        "## Interpretation",
        f"- Mean alpha power: {aggregate['alpha']['mean']:.4f}",
        f"- Mean signal quality: {aggregate['signal_quality']['mean']:.4f}",
        f"- Highest SQ subject: {max(results, key=lambda r: r['signal_quality'])['subject']}",
        "",
        "## Limitations",
        "- Engineering/scientific evaluation only — not clinical validation",
        "- Single dataset, 10 subjects, no control condition",
        "- MNE preprocessing applied for artifact reduction",
        "- Bandpower is experimental proxy, not clinical biomarker",
        "",
        report["disclaimer"],
    ])
    with open(mp, "w") as f:
        f.write("\n".join(lines))

    # Plots
    if not args.no_plots:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))
            for subj, curve in list(all_psd_curves.items())[:6]:
                ax.semilogy(curve["freqs"], curve["psd"], alpha=0.6, label=subj)
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("PSD (dB)")
            ax.set_title("OpenMIIR PSD Summary (6 subjects)")
            ax.legend(fontsize=7)
            fig.savefig(_figures_path(f"{prefix}_psd_summary.png"), dpi=100)
            plt.close(fig)

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            bps = ["delta", "theta", "alpha", "beta"]
            np.arange(len(bps))
            data_m = np.array([[r[b] for b in bps] for r in results])
            ax2.boxplot([data_m[:, i] for i in range(len(bps))], tick_labels=bps)
            ax2.set_ylabel("Relative bandpower")
            ax2.set_title("OpenMIIR Bandpower Distribution")
            fig2.savefig(_figures_path(f"{prefix}_bandpower_distribution.png"), dpi=100)
            plt.close(fig2)
        except Exception:
            pass

    print(
        f"Scientific analysis: {jp}", file=sys.stderr,
    )
    print(
        f"  Subjects: {len(results)} | "
        f"Alpha mean: {aggregate['alpha']['mean']:.4f} | "
        f"SQ: {aggregate['signal_quality']['mean']:.4f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

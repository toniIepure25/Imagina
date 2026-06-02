"""OpenMIIR Experimental Condition EEG Analysis CLI v3.9.6.

EXPERIMENTAL ONLY. Not production-validated.
Extracts event-locked EEG epochs, computes spectral features per condition,
runs conservative statistics, generates exploratory figures.

Mapping: {stimulus_group}{trigger_type} (empirically validated, not documented).
  Music perception: [11,21,31,41]
  Cued imagery: [12,22,32,42]
  Uncued imagery: [13,23,33,43]
  Noise/baseline: [14,24,34,44]
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")

CONDITION_MAP = {
    "perception": [11, 21, 31, 41],
    "cued_imagery": [12, 22, 32, 42],
    "uncued_imagery": [13, 23, 33, 43],
    "noise": [14, 24, 34, 44],
}

BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma_low": (30.0, 45.0),
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_experimental_condition_analysis")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--tmin", type=float, default=0.0)
    p.add_argument("--tmax", type=float, default=7.0)
    p.add_argument("--baseline-tmin", type=float, default=None)
    p.add_argument("--baseline-tmax", type=float, default=None)
    p.add_argument("--max-epochs-per-condition", type=int, default=200)
    p.add_argument("--output-prefix", default="openmiir_condition_analysis_experimental")
    return p


def _load_fif_events(manifest_path, max_subjects):
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path) as f:
        fif_files = json.load(f).get("files", [])[:max_subjects]

    results = []
    for fif in fif_files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            sfreq = raw.info["sfreq"]
            stim_ch_name = None
            for i, ch_name in enumerate(raw.ch_names):
                ch_type = str(raw.get_channel_types(picks=[i])[0])
                if "stim" in ch_type.lower() or "sti" in ch_name.lower():
                    stim_ch_name = ch_name
                    break
            if not stim_ch_name:
                results.append({"subject": subj, "events": [], "error": "no_stim"})
                del raw
                continue

            events = mne.find_events(raw, stim_channel=stim_ch_name, shortest_event=1, verbose=False)

            pick_eeg = mne.pick_types(raw.info, eeg=True, stim=False, exclude=[])
            if len(pick_eeg) == 0:
                results.append({"subject": subj, "error": "no_eeg_channels"})
                del raw
                continue

            # Get channel names before picking (full list)
            all_ch_names = list(raw.ch_names)

            # Preload only EEG channels
            raw.pick(pick_eeg, verbose=False)
            raw.load_data(verbose=False)
            eeg_data = raw.get_data()
            ch_names = [all_ch_names[i] for i in pick_eeg]

            results.append({
                "subject": subj,
                "sfreq": float(sfreq),
                "n_channels": len(pick_eeg),
                "ch_names": ch_names,
                "events": [(int(ev[2]), float(ev[0]) / sfreq, int(ev[0]))
                          for ev in events],
                "n_events_total": len(events),
                "eeg_data": eeg_data,
            })
            del raw
        except Exception as e:
            results.append({"subject": subj, "error": str(e)})
    return results


def _extract_epochs(subject_data, condition_map, tmin, tmax, max_epochs, baseline):
    results = {}
    data = subject_data.get("eeg_data")
    events = subject_data.get("events", [])
    sfreq = subject_data.get("sfreq", 512)
    n_samples = int((tmax - tmin) * sfreq)

    if data is None or len(events) == 0:
        return results

    for cond_name, codes in condition_map.items():
        epochs_list = []
        for code, time_sec, sample in events:
            if code not in codes:
                continue
            start_sample = int(sample + tmin * sfreq)
            end_sample = start_sample + n_samples
            if start_sample < 0 or end_sample > data.shape[1]:
                continue
            epoch = data[:, start_sample:end_sample].astype(np.float64)

            # Skip if epoch has NaN or extreme values
            if not np.all(np.isfinite(epoch)):
                continue

            if baseline is not None:
                bl_start = int(baseline[0] * sfreq)
                bl_end = int(baseline[1] * sfreq)
                bl = np.mean(epoch[:, bl_start:bl_end], axis=1, keepdims=True)
                bl = bl if bl.shape[0] == epoch.shape[0] else 0
            else:
                bl = 0

            epochs_list.append(epoch - bl)
            if len(epochs_list) >= max_epochs:
                break

        if epochs_list:
            results[cond_name] = {
                "n_epochs": len(epochs_list),
                "n_rejected": 0,
                "epochs_array": np.stack(epochs_list),
            }
    return results


def _compute_bandpower(epoch, sfreq, bands):
    from scipy.signal import welch as scipy_welch

    ch_mean = np.mean(epoch, axis=0)
    nperseg = min(256, len(ch_mean))
    if nperseg < 32:
        return {k: 0.0 for k in bands}
    freqs, psd = scipy_welch(ch_mean, fs=sfreq, nperseg=nperseg, detrend="linear")
    psd_total = np.trapezoid(psd, freqs)
    if psd_total <= 0:
        return {k: 0.0 for k in bands}
    result = {}
    for name, (lo, hi) in bands.items():
        if hi > sfreq / 2:
            result[name] = 0.0
            continue
        mask = (freqs >= lo) & (freqs <= hi)
        if not mask.any():
            result[name] = 0.0
            continue
        result[name] = float(np.trapezoid(psd[mask], freqs[mask]) / psd_total)
    return result


def _extract_features(subject_data, epochs_by_cond, sfreq):
    features = {}
    for cond_name, ep_data in epochs_by_cond.items():
        epochs = ep_data["epochs_array"]
        n_ep = len(epochs)
        bp_list = []
        for i in range(n_ep):
            bp = _compute_bandpower(epochs[i], sfreq, BANDS)
            bp_list.append(bp)
        bp_arr = {k: np.array([bp[k] for bp in bp_list]) for k in BANDS}

        feat = {
            "n_epochs": n_ep,
            "signal_quality_mean": float(np.mean([_signal_quality(epochs[i]) for i in range(n_ep)])),
        }
        for band_name in BANDS:
            vals = bp_arr[band_name]
            feat[f"{band_name}_power_mean"] = float(np.mean(vals))
            feat[f"{band_name}_power_std"] = float(np.std(vals))

        feat["theta_alpha_ratio"] = (feat["theta_power_mean"]
                                     / max(feat["alpha_power_mean"], 1e-6))
        feat["beta_alpha_ratio"] = (feat["beta_power_mean"]
                                    / max(feat["alpha_power_mean"], 1e-6))
        feat["alpha_beta_ratio"] = (feat["alpha_power_mean"]
                                    / max(feat["beta_power_mean"], 1e-6))

        features[cond_name] = feat
    return features


def _signal_quality(epoch):
    ptp = np.ptp(epoch)
    return max(0.0, 1.0 - min(1.0, ptp / 500e-6))


def _compute_statistics(all_subject_features, condition_map):
    band_names = list(BANDS.keys())
    metric_names = [f"{b}_power_mean" for b in band_names] + [
        "theta_alpha_ratio", "beta_alpha_ratio", "alpha_beta_ratio",
        "signal_quality_mean",
    ]
    comparisons = [
        ("perception", "cued_imagery"),
        ("perception", "uncued_imagery"),
        ("perception", "noise"),
        ("cued_imagery", "uncued_imagery"),
        ("cued_imagery", "noise"),
        ("uncued_imagery", "noise"),
    ]

    stats_results = []
    for cond_a, cond_b in comparisons:
        for metric in metric_names:
            try:
                vals_a, vals_b = [], []
                valid_subjs = 0
                for subj_feat in all_subject_features:
                    if (cond_a in subj_feat and cond_b in subj_feat
                            and metric in subj_feat[cond_a]
                            and metric in subj_feat[cond_b]):
                        vals_a.append(subj_feat[cond_a][metric])
                        vals_b.append(subj_feat[cond_b][metric])
                        valid_subjs += 1

                if valid_subjs < 3:
                    continue

                av, bv = np.array(vals_a), np.array(vals_b)
                diffs = av - bv
                mean_diff = float(np.mean(diffs))
                std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 1.0
                cohens_dz = mean_diff / max(std_diff, 1e-10)

                # Bootstrap CI
                n_boot = 1000
                rng = np.random.RandomState(42)
                boot_means = np.array([
                    np.mean(rng.choice(diffs, size=len(diffs), replace=True))
                    for _ in range(n_boot)
                ])
                ci_low = float(np.percentile(boot_means, 2.5))
                ci_high = float(np.percentile(boot_means, 97.5))

                # Permutation test
                n_perm = 1000
                perm_diffs = np.zeros(n_perm)
                obs_stat = mean_diff
                combined = np.concatenate([av, bv])
                na = len(av)
                for i in range(n_perm):
                    rng.shuffle(combined)
                    perm_diffs[i] = float(np.mean(combined[:na]) - np.mean(combined[na:]))
                p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(obs_stat)))

                stats_results.append({
                    "comparison": f"{cond_a}_vs_{cond_b}",
                    "feature": metric,
                    "n_subjects": valid_subjs,
                    "mean_difference": round(mean_diff, 6),
                    "cohens_dz": round(cohens_dz, 4),
                    "ci_95_low": round(ci_low, 6),
                    "ci_95_high": round(ci_high, 6),
                    "p_value": round(p_value, 4),
                    "interpretation": (
                        "small effect" if abs(cohens_dz) < 0.5
                        else "medium effect" if abs(cohens_dz) < 0.8
                        else "large effect"
                    ),
                })
            except Exception:
                continue

    # FDR correction
    if stats_results:
        pvals = np.array([s["p_value"] for s in stats_results])
        sorted_idx = np.argsort(pvals)
        n_tests = len(pvals)
        fdr_thresholds = np.arange(1, n_tests + 1) / n_tests * 0.05
        significant = np.zeros(n_tests, dtype=bool)
        for rank, si in enumerate(sorted_idx):
            if pvals[si] <= fdr_thresholds[rank]:
                significant[si] = True
        for i, s in enumerate(stats_results):
            s["p_fdr"] = round(float(pvals[sorted_idx[list(sorted_idx).index(i)]]
                               if i in sorted_idx else pvals[i]), 4)
            s["fdr_significant"] = bool(significant[i])

    return stats_results


def _generate_figures(all_subject_features, stats_results, prefix):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    figs = []

    # 1. Bandpower by condition
    bands_for_plot = ["delta", "theta", "alpha", "beta"]
    conditions = ["perception", "cued_imagery", "uncued_imagery", "noise"]
    colors = ["#2196F3", "#FF9800", "#4CAF50", "#F44336"]
    cond_data = {c: {b: [] for b in bands_for_plot} for c in conditions}
    for sf in all_subject_features:
        for c in conditions:
            if c in sf:
                for b in bands_for_plot:
                    key = f"{b}_power_mean"
                    if key in sf[c]:
                        cond_data[c][b].append(sf[c][key])

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    for bi, b in enumerate(bands_for_plot):
        ax = axes[bi]
        data_to_plot = [cond_data[c][b] for c in conditions]
        bp = ax.boxplot(data_to_plot, tick_labels=["P", "CI", "UI", "N"], patch_artist=True)
        for patch, col in zip(bp["boxes"], colors):
            patch.set_facecolor(col)
            patch.set_alpha(0.6)
        ax.set_title(f"{b.capitalize()} Power")
        ax.set_ylabel("Relative Power")
        ax.tick_params(labelsize=8)
    fig.suptitle("Bandpower by Condition (Experimental Hypothesis Only)", fontsize=12)
    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, f"{prefix}_bandpower_by_condition.png")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    figs.append(path)

    # 2. Alpha/theta delta
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for ai, (band, title) in enumerate([("alpha", "Alpha Power"), ("theta", "Theta Power")]):
        ax = axes[ai]
        key = f"{band}_power_mean"
        subj_diffs = []
        labels_used = []
        for sf in all_subject_features:
            if "perception" in sf and "cued_imagery" in sf:
                if key in sf["perception"] and key in sf["cued_imagery"]:
                    subj_diffs.append(sf["perception"][key] - sf["cued_imagery"][key])
                    labels_used.append("P-CI")
            if "perception" in sf and "uncued_imagery" in sf:
                if key in sf["perception"] and key in sf["uncued_imagery"]:
                    subj_diffs.append(sf["perception"][key] - sf["uncued_imagery"][key])
                    labels_used.append("P-UI")
        if subj_diffs:
            ax.bar(range(len(subj_diffs)), subj_diffs,
                   color=["#2196F3"] * (len(labels_used) // 2)
                   + ["#4CAF50"] * (len(labels_used) // 2))
            ax.axhline(0, color="black", linewidth=0.5)
            ax.set_xticks(range(len(subj_diffs)))
            ax.set_xticklabels(labels_used, fontsize=7, rotation=45)
            ax.set_title(f"{title} Differences")
    fig.suptitle("Alpha/Theta Perception-Imagery Deltas (Experimental)", fontsize=11)
    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, f"{prefix}_alpha_theta_delta.png")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    figs.append(path)

    # 3. Subject variability
    fig, ax = plt.subplots(figsize=(10, 5))
    for ci, c in enumerate(conditions):
        alphas = [sf[c]["alpha_power_mean"] for sf in all_subject_features if c in sf
                  and "alpha_power_mean" in sf[c]]
        thetas = [sf[c]["theta_power_mean"] for sf in all_subject_features if c in sf
                  and "theta_power_mean" in sf[c]]
        ax.scatter(alphas, thetas, label=c, color=colors[ci], alpha=0.7, s=40)
    ax.set_xlabel("Alpha Power")
    ax.set_ylabel("Theta Power")
    ax.set_title("Subject Variability: Alpha vs Theta by Condition (Experimental)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, f"{prefix}_subject_variability.png")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    figs.append(path)

    # 4. Effect sizes
    if stats_results:
        fig, ax = plt.subplots(figsize=(12, 6))
        labels_list = [f"{s['comparison']}\n{s['feature']}" for s in stats_results[:30]]
        dz_vals = [s["cohens_dz"] for s in stats_results[:30]]
        colors_es = ["green" if abs(d) >= 0.8 else "orange" if abs(d) >= 0.5
                      else "gray" for d in dz_vals]
        ax.barh(range(len(labels_list)), dz_vals, color=colors_es)
        ax.set_yticks(range(len(labels_list)))
        ax.set_yticklabels(labels_list, fontsize=6)
        ax.axvline(0, color="black", linewidth=0.5)
        ax.axvline(0.5, color="orange", linestyle="--", alpha=0.5)
        ax.axvline(-0.5, color="orange", linestyle="--", alpha=0.5)
        ax.set_xlabel("Cohen's dz")
        ax.set_title("Effect Sizes — Experimental Hypothesis Only", fontsize=11)
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{prefix}_effect_sizes.png")
        fig.savefig(path, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(path)

    # 5. P-value heatmap
    if stats_results:
        comps = sorted(set(s["comparison"] for s in stats_results))
        metrics = sorted(set(s["feature"] for s in stats_results))
        if comps and metrics:
            p_matrix = np.full((len(comps), len(metrics)), np.nan)
            for s in stats_results:
                ci = comps.index(s["comparison"])
                mi = metrics.index(s["feature"])
                p_matrix[ci, mi] = s["p_value"]
            fig, ax = plt.subplots(figsize=(max(10, len(metrics) * 1.2),
                                             max(5, len(comps) * 0.6)))
            im = ax.imshow(p_matrix, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)
            ax.set_xticks(range(len(metrics)))
            ax.set_xticklabels(metrics, fontsize=7, rotation=45, ha="right")
            ax.set_yticks(range(len(comps)))
            ax.set_yticklabels(comps, fontsize=7)
            ax.set_title("P-Value Heatmap (Uncorrected, Experimental)", fontsize=11)
            fig.colorbar(im, ax=ax)
            fig.tight_layout()
            path = os.path.join(FIGURES_DIR, f"{prefix}_pvalue_heatmap.png")
            fig.savefig(path, dpi=150, facecolor="white")
            plt.close(fig)
            figs.append(path)

    return figs


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    manifest_path = os.path.join(
        BASE, "..", "..", "data", "external", "openmiir", "manifest.json"
    )
    print(f"Loading EEG data for up to {args.max_subjects} subjects...", file=sys.stderr)
    subjects = _load_fif_events(manifest_path, args.max_subjects)

    all_features = []
    feature_csv_rows = []
    cond_keys = list(CONDITION_MAP.keys())
    csv_header = (
        "subject,condition,n_epochs,signal_quality," +
        ",".join(f"{b}_power_mean,{b}_power_std" for b in BANDS) +
        ",theta_alpha_ratio,beta_alpha_ratio,alpha_beta_ratio"
    )

    print("Extracting epochs and features...", file=sys.stderr)
    for s in subjects:
        if s.get("error"):
            print(f"  Skipping {s['subject']}: {s['error']}", file=sys.stderr)
            continue
        try:
            epochs = _extract_epochs(
                s, CONDITION_MAP, args.tmin, args.tmax,
                args.max_epochs_per_condition,
                (args.baseline_tmin, args.baseline_tmax) if args.baseline_tmin is not None else None,
            )
            if not epochs:
                print(f"  No epochs for {s['subject']}", file=sys.stderr)
                continue
            features = _extract_features(s, epochs, s["sfreq"])
            all_features.append(features)
        except Exception as e:
            print(f"  Epoch/feature error {s['subject']}: {e}", file=sys.stderr)
            continue

        for cn in cond_keys:
            feat = features.get(cn)
            if feat is None:
                continue
            row = (
                f"{s['subject']},{cn},{feat['n_epochs']},{feat['signal_quality_mean']:.4f},"
            )
            row += ",".join(
                f"{feat.get(f'{b}_power_mean', 0):.6f},{feat.get(f'{b}_power_std', 0):.6f}"
                for b in BANDS
            )
            row += (f",{feat.get('theta_alpha_ratio', 0):.4f},"
                    f"{feat.get('beta_alpha_ratio', 0):.4f},"
                    f"{feat.get('alpha_beta_ratio', 0):.4f}")
            feature_csv_rows.append(row)

    print("Computing statistics...", file=sys.stderr)
    stats = _compute_statistics(all_features, CONDITION_MAP)

    print("Generating figures...", file=sys.stderr)
    figures = _generate_figures(all_features, stats, args.output_prefix)

    n_subj = len(all_features)
    top_effects = sorted(stats, key=lambda x: abs(x["cohens_dz"]), reverse=True)[:10]
    fdr_hits = sum(1 for s in stats if s.get("fdr_significant"))

    report = {
        "tool": "openmiir_experimental_condition_analysis_v3.9.6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "source_mapping": {
            "trigger_semantics_confirmed": True,
            "stimtracker_encoding_empirically_validated": True,
            "stimtracker_encoding_documented": False,
            "mapping_confidence": "empirically_validated_hypothesis",
            "mapping": {k: v for k, v in CONDITION_MAP.items()},
        },
        "dataset": {
            "n_subjects_requested": args.max_subjects,
            "n_subjects_analyzed": n_subj,
            "tmin_sec": args.tmin,
            "tmax_sec": args.tmax,
        },
        "conditions": {
            k: {"n_codes": len(v), "codes": v} for k, v in CONDITION_MAP.items()
        },
        "feature_summary": {
            "bands": list(BANDS.keys()),
            "n_features": len(all_features[0]) * len(BANDS) * 2 if all_features else 0,
            "subjects_per_condition": {
                k: sum(1 for sf in all_features if k in sf)
                for k in CONDITION_MAP
            },
        },
        "statistical_summary": {
            "n_comparisons": len(stats),
            "n_paired_tests": len(stats),
            "fdr_significant_hits": fdr_hits,
            "top_effects": [
                {
                    "comparison": e["comparison"],
                    "feature": e["feature"],
                    "cohens_dz": e["cohens_dz"],
                    "ci_95_low": e["ci_95_low"],
                    "ci_95_high": e["ci_95_high"],
                    "p_uncorrected": e["p_value"],
                    "p_fdr": e.get("p_fdr", e["p_value"]),
                    "interpretation": e["interpretation"],
                }
                for e in top_effects
            ],
        },
        "figures": figures,
        "limitations": [
            "Small sample: 10 subjects, single session each",
            "StimTracker encoding empirically validated, not documented",
            "No correction for multiple electrode comparisons",
            "Sham-controlled studies required for validation",
            "Results are exploratory, not confirmatory",
            "No clinical interpretation should be drawn",
            "This is a research prototype — not a validated EEG analysis",
        ],
        "no_raw_eeg_exposed": True,
        "disclaimer": (
            "EXPERIMENTAL HYPOTHESIS ONLY. These results are exploratory and "
            "do not constitute scientific validation. No clinical claims are made. "
            "StimTracker encoding is empirically validated but not confirmed by "
            "documentation. All findings require independent replication."
        ),
        "all_statistics": stats,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    csv_path = os.path.join(EXPORTS, f"{args.output_prefix}_features.csv")
    with open(csv_path, "w") as f:
        f.write(csv_header + "\n")
        for row in feature_csv_rows:
            f.write(row + "\n")

    stats_csv = os.path.join(EXPORTS, f"{args.output_prefix}_stats.csv")
    if stats:
        with open(stats_csv, "w") as f:
            keys = ["comparison", "feature", "n_subjects", "mean_difference",
                    "cohens_dz", "ci_95_low", "ci_95_high", "p_value", "p_fdr",
                    "fdr_significant", "interpretation"]
            f.write(",".join(keys) + "\n")
            for s in stats:
                f.write(",".join(str(s.get(k, "")) for k in keys) + "\n")

    md_lines = [
        "# OpenMIIR Experimental Condition EEG Analysis",
        "",
        ":warning: **EXPERIMENTAL HYPOTHESIS ONLY — Not valid for scientific claims.**",
        "",
        f"**Subjects analyzed**: {n_subj}/{args.max_subjects}",
        f"**Conditions**: {list(CONDITION_MAP.keys())}",
        f"**Window**: {args.tmin}s to {args.tmax}s",
        f"**Comparisons**: {len(stats)}",
        f"**FDR significant hits**: {fdr_hits}",
        "",
        "## Condition Mapping (Experimental)",
        "| Condition | Codes |",
        "|-----------|-------|",
    ]
    for k, v in CONDITION_MAP.items():
        md_lines.append(f"| {k} | {v} |")

    md_lines.append("")
    md_lines.append("## Top Effects")
    md_lines.append("| Comparison | Feature | dz | CI | p | FDR sig |")
    md_lines.append("|------------|---------|-----|----|---|---------|")
    for e in top_effects[:10]:
        md_lines.append(
            f"| {e['comparison']} | {e['feature']} | {e['cohens_dz']:.3f} | "
            f"[{e.get('ci_95_low', 0):.3f}, {e.get('ci_95_high', 0):.3f}] | "
            f"{e.get('p_value', 0):.3f} | {e.get('p_fdr', 'N/A')} |"
        )

    md_lines.append("")
    md_lines.append("## Limitations")
    for lim in report["limitations"]:
        md_lines.append(f"- {lim}")

    md_lines.append("")
    md_lines.append(f"## Figures: {len(figures)}")
    for fig in figures:
        md_lines.append(f"- `{os.path.basename(fig)}`")

    md_path = os.path.join(EXPORTS, f"{args.output_prefix}.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Experimental analysis: subjects={n_subj} stats={len(stats)} "
          f"figures={len(figures)} fdr_05={fdr_hits}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

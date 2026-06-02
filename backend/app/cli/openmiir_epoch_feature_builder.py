"""OpenMIIR Epoch-Level Feature Builder v4.0.

Extracts rich spectral/regional/temporal/quality features per epoch.
Experimental only — not production-validated.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")

CONDITION_MAP = {
    "perception": [11, 21, 31, 41],
    "cued_imagery": [12, 22, 32, 42],
    "uncued_imagery": [13, 23, 33, 43],
    "noise": [14, 24, 34, 44],
}

BANDS = {
    "delta": (0.5, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0), "gamma_low": (30.0, 45.0),
}

REGION_PATTERNS = {
    "frontal": ["Fp", "AF", "F"],
    "central": ["C"],
    "temporal": ["T", "TP", "FT"],
    "parietal": ["P"],
    "occipital": ["O", "PO"],
}

FEATURE_COLUMNS = [
    "subject", "epoch_id", "condition", "event_code", "stimulus_group",
    "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
    "signal_quality", "artifact_rejected",
    "delta_power", "theta_power", "alpha_power", "beta_power", "gamma_low_power",
    "theta_alpha_ratio", "beta_alpha_ratio", "alpha_beta_ratio",
    "spectral_entropy", "total_power", "log_total_power",
    "alpha_frontal", "theta_frontal", "alpha_central", "theta_central",
    "alpha_parietal", "theta_parietal", "alpha_occipital", "theta_occipital",
    "alpha_temporal", "theta_temporal",
    "alpha_early", "alpha_mid", "alpha_late",
    "theta_early", "theta_mid", "theta_late",
    "peak_to_peak", "variance", "flat_channel_ratio",
    "high_amplitude_ratio",
    "analysis_mode",
]


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_epoch_feature_builder")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--tmin", type=float, default=0.0)
    p.add_argument("--tmax", type=float, default=7.0)
    p.add_argument("--max-epochs-per-condition", type=int, default=200)
    p.add_argument("--output-prefix", default="openmiir_epoch_features_experimental")
    return p


def _load_subject(fif_path):
    import mne

    raw = mne.io.read_raw_fif(fif_path, preload=False, verbose=False)
    sfreq = raw.info["sfreq"]
    all_ch_names = list(raw.ch_names)

    stim_ch = None
    for i, ch_name in enumerate(raw.ch_names):
        ct = str(raw.get_channel_types(picks=[i])[0])
        if "stim" in ct.lower() or "sti" in ch_name.lower():
            stim_ch = ch_name
            break

    if not stim_ch:
        del raw
        return None

    events = mne.find_events(raw, stim_channel=stim_ch, shortest_event=1, verbose=False)

    pick_eeg = mne.pick_types(raw.info, eeg=True, stim=False, exclude=[])
    if len(pick_eeg) == 0:
        del raw
        return None

    ch_names = [all_ch_names[i] for i in pick_eeg]
    raw.pick(pick_eeg, verbose=False)
    raw.load_data(verbose=False)
    data = raw.get_data()
    result = {
        "sfreq": float(sfreq), "ch_names": ch_names, "data": data,
        "events": [(int(ev[2]), int(ev[0])) for ev in events],
        "n_channels": len(pick_eeg),
    }
    del raw
    return result


def _channel_region_map(ch_names):
    region_map = {}
    for i, ch in enumerate(ch_names):
        for region, prefixes in REGION_PATTERNS.items():
            if any(ch.startswith(p) for p in prefixes):
                region_map.setdefault(region, []).append(i)
                break
    return region_map


def _bandpower(psd_slice, freqs, lo, hi, sfreq):
    if hi > sfreq / 2:
        return 0.0
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        return 0.0
    return float(np.trapezoid(psd_slice[mask], freqs[mask]))


def _compute_epoch_features(epoch, sfreq, ch_names, region_map, code, subj, epoch_idx):
    from scipy.signal import welch as scipy_welch

    n_ch, n_samp = epoch.shape
    ch_mean = np.mean(epoch, axis=0)
    nperseg = min(256, n_samp)
    if nperseg < 32:
        return None

    freqs, psd = scipy_welch(ch_mean, fs=sfreq, nperseg=nperseg, detrend="linear")
    psd_total = float(np.trapezoid(psd, freqs)) or 1e-10

    bp = {}
    for band_name, (lo, hi) in BANDS.items():
        bp[band_name] = _bandpower(psd, freqs, lo, hi, sfreq) / psd_total

    # Spectral entropy
    psd_norm = psd / (psd.sum() + 1e-12)
    sent = -float(np.sum(psd_norm * np.log(psd_norm + 1e-12)))

    # Channel-region features
    region_feats = {}
    for region, ch_indices in region_map.items():
        if not ch_indices:
            continue
        reg_data = np.mean(epoch[ch_indices], axis=0)
        _, reg_psd = scipy_welch(reg_data, fs=sfreq, nperseg=nperseg, detrend="linear")
        reg_total = float(np.trapezoid(reg_psd, freqs)) or 1e-10
        for band_name, (lo, hi) in [("alpha", BANDS["alpha"]), ("theta", BANDS["theta"])]:
            region_feats[f"{band_name}_{region}"] = _bandpower(reg_psd, freqs, lo, hi, sfreq) / reg_total

    # Temporal split features
    n_third = n_samp // 3
    terciles = {"early": epoch[:, :n_third], "mid": epoch[:, n_third:2 * n_third],
                 "late": epoch[:, 2 * n_third:]}
    temporal_feats = {}
    for key, terc_data in terciles.items():
        if terc_data.shape[1] < 32:
            continue
        tm = np.mean(terc_data, axis=0)
        t_nperseg = min(128, terc_data.shape[1])
        _, tpsd = scipy_welch(tm, fs=sfreq, nperseg=t_nperseg, detrend="linear")
        t_freqs = np.fft.rfftfreq(len(tm), d=1.0 / sfreq)
        ttotal = float(np.trapezoid(tpsd, t_freqs[:len(tpsd)])) or 1e-10
        for band_name in ["alpha", "theta"]:
            lo, hi = BANDS[band_name]
            if hi > sfreq / 2:
                continue
            mask = (t_freqs[:len(tpsd)] >= lo) & (t_freqs[:len(tpsd)] <= hi)
            if mask.any():
                t_freqs_mask = t_freqs[:len(tpsd)][mask]
                temporal_feats[f"{band_name}_{key}"] = float(np.trapezoid(tpsd[mask], t_freqs_mask)) / ttotal

    # Quality features
    ptp = float(np.ptp(epoch))
    variance = float(np.var(epoch))
    ch_range = np.ptp(epoch, axis=1)
    flat = float(np.mean((ch_range < 1e-7).astype(float)))
    high_amp = float(np.mean((np.abs(epoch) > 200e-6).astype(float)))
    sig_quality = float(np.clip(1.0 - min(1.0, ptp / 500e-6), 0, 1))

    trigger_type = code % 10 if 10 <= code <= 49 else 0
    stimulus_group = code // 10 if 10 <= code <= 49 else 0

    row = {
        "subject": subj, "epoch_id": epoch_idx, "condition": None,
        "event_code": code, "stimulus_group": stimulus_group,
        "trigger_type": trigger_type,
        "sfreq": sfreq, "n_channels": n_ch, "epoch_duration_sec": round(n_samp / sfreq, 3),
        "signal_quality": round(sig_quality, 4), "artifact_rejected": 0,
        "delta_power": round(bp.get("delta", 0), 6),
        "theta_power": round(bp.get("theta", 0), 6),
        "alpha_power": round(bp.get("alpha", 0), 6),
        "beta_power": round(bp.get("beta", 0), 6),
        "gamma_low_power": round(bp.get("gamma_low", 0), 6),
        "theta_alpha_ratio": round(bp.get("theta", 0) / max(bp.get("alpha", 0), 1e-6), 4),
        "beta_alpha_ratio": round(bp.get("beta", 0) / max(bp.get("alpha", 0), 1e-6), 4),
        "alpha_beta_ratio": round(bp.get("alpha", 0) / max(bp.get("beta", 0), 1e-6), 4),
        "spectral_entropy": round(sent, 4),
        "total_power": round(psd_total, 6),
        "log_total_power": round(np.log(psd_total + 1e-10), 4),
        "alpha_frontal": round(region_feats.get("alpha_frontal", 0), 6),
        "theta_frontal": round(region_feats.get("theta_frontal", 0), 6),
        "alpha_central": round(region_feats.get("alpha_central", 0), 6),
        "theta_central": round(region_feats.get("theta_central", 0), 6),
        "alpha_parietal": round(region_feats.get("alpha_parietal", 0), 6),
        "theta_parietal": round(region_feats.get("theta_parietal", 0), 6),
        "alpha_occipital": round(region_feats.get("alpha_occipital", 0), 6),
        "theta_occipital": round(region_feats.get("theta_occipital", 0), 6),
        "alpha_temporal": round(region_feats.get("alpha_temporal", 0), 6),
        "theta_temporal": round(region_feats.get("theta_temporal", 0), 6),
        "alpha_early": round(temporal_feats.get("alpha_early", 0), 6),
        "alpha_mid": round(temporal_feats.get("alpha_mid", 0), 6),
        "alpha_late": round(temporal_feats.get("alpha_late", 0), 6),
        "theta_early": round(temporal_feats.get("theta_early", 0), 6),
        "theta_mid": round(temporal_feats.get("theta_mid", 0), 6),
        "theta_late": round(temporal_feats.get("theta_late", 0), 6),
        "peak_to_peak": round(ptp, 6),
        "variance": round(variance, 6),
        "flat_channel_ratio": round(flat, 4),
        "high_amplitude_ratio": round(high_amp, 4),
        "analysis_mode": "experimental_hypothesis_only",
    }
    return row


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    manifest_path = os.path.join(
        BASE, "..", "..", "data", "external", "openmiir", "manifest.json"
    )
    if not os.path.exists(manifest_path):
        print("Manifest not found", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        fif_files = json.load(f).get("files", [])[:args.max_subjects]

    csv_path = os.path.join(EXPORTS, f"{args.output_prefix}.csv")
    all_rows = []
    epoch_counts = {"per_subject": {}, "per_condition": defaultdict(int)}
    n_subjects_ok = 0

    print(f"Processing {len(fif_files)} subjects...", file=sys.stderr)

    with open(csv_path, "w") as csv_f:
        csv_f.write(",".join(FEATURE_COLUMNS) + "\n")

        for fif in fif_files:
            subj = os.path.splitext(os.path.basename(fif))[0]
            subj_data = _load_subject(fif)
            if subj_data is None:
                print(f"  {subj}: skipped (no stim/EEG)", file=sys.stderr)
                continue

            region_map = _channel_region_map(subj_data["ch_names"])
            epoch_count = 0

            for code, sample in subj_data["events"]:
                cond_found = None
                for cond_name, cond_codes in CONDITION_MAP.items():
                    if code in cond_codes:
                        cond_found = cond_name
                        break
                if cond_found is None:
                    continue

                start = int(sample + args.tmin * subj_data["sfreq"])
                end = start + int((args.tmax - args.tmin) * subj_data["sfreq"])
                if start < 0 or end > subj_data["data"].shape[1]:
                    continue

                epoch = subj_data["data"][:, start:end].astype(np.float64)
                if not np.all(np.isfinite(epoch)):
                    continue

                row = _compute_epoch_features(
                    epoch, subj_data["sfreq"], subj_data["ch_names"],
                    region_map, code, subj, epoch_count,
                )
                if row is None:
                    continue

                row["condition"] = cond_found
                csv_f.write(",".join(str(row.get(c, "")) for c in FEATURE_COLUMNS) + "\n")
                all_rows.append(row)
                epoch_count += 1
                epoch_counts["per_condition"][cond_found] += 1

                if epoch_count >= args.max_epochs_per_condition * 4:
                    break

            epoch_counts["per_subject"][subj] = epoch_count
            n_subjects_ok += 1
            print(f"  {subj}: {epoch_count} epochs", file=sys.stderr)

    report = {
        "tool": "openmiir_epoch_feature_builder_v4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "n_subjects": n_subjects_ok,
        "n_epochs_total": sum(epoch_counts["per_subject"].values()),
        "n_epochs_per_subject": epoch_counts["per_subject"],
        "n_epochs_per_condition": dict(epoch_counts["per_condition"]),
        "n_features": len(FEATURE_COLUMNS),
        "feature_columns": FEATURE_COLUMNS,
        "tmin_sec": args.tmin,
        "tmax_sec": args.tmax,
        "condition_mapping": {k: v for k, v in CONDITION_MAP.items()},
        "csv_path": csv_path,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    md_lines = [
        "# OpenMIIR Epoch-Level Feature Builder",
        f"**Subjects**: {n_subjects_ok}",
        f"**Epochs**: {report['n_epochs_total']}",
        f"**Features**: {len(FEATURE_COLUMNS)}",
        f"**Per condition**: {dict(epoch_counts['per_condition'])}",
        "",
        ":warning: Experimental hypothesis only — not production-validated.",
    ]
    md_path = os.path.join(EXPORTS, f"{args.output_prefix}.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Epoch features: {n_subjects_ok} subjects, {report['n_epochs_total']} epochs, "
          f"{len(FEATURE_COLUMNS)} features", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

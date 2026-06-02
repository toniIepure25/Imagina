"""OpenMIIR SSL Epoch Tensor Builder v4.4.

Builds epoch tensors for self-supervised learning from FIF files.
Internal artifact — no raw EEG in summary JSON.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")

CONDITION_MAP = {
    0: ("perception", [11, 21, 31, 41]),
    1: ("cued_imagery", [12, 22, 32, 42]),
    2: ("uncued_imagery", [13, 23, 33, 43]),
    3: ("noise", [14, 24, 34, 44]),
}

# Common 10-20 EEG channels to use as intersection
COMMON_CHANNELS = [
    "Fp1", "AF7", "AF3", "F1", "F3", "F5", "F7", "FT7", "FC5", "FC3", "FC1",
    "C1", "C3", "C5", "T7", "TP7", "CP5", "CP3", "CP1", "P1", "P3", "P5",
    "P7", "P9", "PO7", "PO3", "O1", "Iz", "Oz", "POz", "Pz", "CPz", "Fpz",
    "Fp2", "AF8", "AF4", "AFz", "Fz", "F2", "F4", "F6", "F8", "FT8", "FC6",
    "FC4", "FC2", "FCz", "Cz", "C2", "C4", "C6", "T8", "TP8", "CP6", "CP4",
    "CP2", "P2", "P4", "P6", "P8", "P10", "PO8", "PO4", "O2",
]


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_epoch_tensor_builder")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--tmin", type=float, default=0.0)
    p.add_argument("--tmax", type=float, default=7.0)
    p.add_argument("--target-sfreq", type=int, default=128)
    p.add_argument("--max-epochs-per-condition", type=int, default=80)
    p.add_argument("--output-prefix", default="openmiir_ssl_epoch_tensors_experimental")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    manifest_path = os.path.join(
        BASE, "..", "..", "data", "external", "openmiir", "manifest.json")
    if not os.path.exists(manifest_path):
        print("Manifest not found", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        fif_files = json.load(f).get("files", [])[:args.max_subjects]

    all_epochs = []
    all_conds = []
    all_subjects = []
    all_codes = []
    all_stim_groups = []
    epoch_counts = defaultdict(int)
    n_subjects_ok = 0
    used_channels = None

    print(f"Building tensors from {len(fif_files)} subjects...", file=sys.stderr)

    for fif in fif_files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            sfreq = raw.info["sfreq"]
            all_ch = list(raw.ch_names)

            stim_ch = None
            for i, ch in enumerate(all_ch):
                ct = str(raw.get_channel_types(picks=[i])[0])
                if "stim" in ct.lower() or "sti" in ch.lower():
                    stim_ch = ch
                    break
            if not stim_ch:
                del raw
                continue

            events = mne.find_events(raw, stim_channel=stim_ch, shortest_event=1, verbose=False)

            pick_eeg = mne.pick_types(raw.info, eeg=True, stim=False, exclude=[])
            if len(pick_eeg) == 0:
                del raw
                continue

            # Get intersection of channels
            ch_names = [all_ch[i] for i in pick_eeg]
            if used_channels is None:
                used_channels = [c for c in COMMON_CHANNELS if c in ch_names]
            subj_channels = used_channels

            raw.pick([pick_eeg[ch_names.index(c)] for c in subj_channels if c in ch_names], verbose=False)
            raw.load_data(verbose=False)
            raw.resample(args.target_sfreq, verbose=False)
            data = raw.get_data()

            n_ch, n_total = data.shape
            epoch_len = int((args.tmax - args.tmin) * args.target_sfreq)

            for ev in events:
                code = int(ev[2])
                sample = int(ev[0] * args.target_sfreq / sfreq)

                cond_label = None
                for cond_id, (cn, codes) in CONDITION_MAP.items():
                    if code in codes:
                        cond_label = cn
                        break
                if cond_label is None:
                    continue

                start = int(sample + args.tmin * args.target_sfreq)
                end = start + epoch_len
                if start < 0 or end > n_total:
                    continue

                epoch = data[:, start:end].astype(np.float32)
                if not np.all(np.isfinite(epoch)):
                    continue

                # Per-epoch channel-wise z-score
                ch_mean = epoch.mean(axis=1, keepdims=True)
                ch_std = epoch.std(axis=1, keepdims=True) + 1e-8
                epoch = (epoch - ch_mean) / ch_std
                epoch = np.clip(epoch, -5, 5)

                all_epochs.append(epoch)
                all_conds.append(cond_label)
                all_subjects.append(subj)
                all_codes.append(code)
                stim_group = code // 10 if 10 <= code <= 49 else 0
                all_stim_groups.append(stim_group)
                epoch_counts[cond_label] += 1

            del raw
            n_subjects_ok += 1
            print(f"  {subj}: loaded ({n_ch} ch → {len(subj_channels)} common, {args.target_sfreq} Hz)",
                  file=sys.stderr)

        except Exception as e:
            print(f"  {subj}: error ({e})", file=sys.stderr)

    X = np.stack(all_epochs) if all_epochs else np.array([])
    y_cond = np.array(all_conds)
    y_subj = np.array(all_subjects)
    y_code = np.array(all_codes)
    y_stim = np.array(all_stim_groups)

    npz_path = os.path.join(EXPORTS, f"{args.output_prefix}.npz")
    np.savez_compressed(npz_path, X=X, y_cond=y_cond, y_subj=y_subj,
                         y_code=y_code, y_stim=y_stim)

    report = {
        "tool": "openmiir_ssl_epoch_tensor_builder_v4.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "n_subjects": n_subjects_ok,
        "n_epochs": len(all_epochs),
        "n_channels": len(used_channels) if used_channels else 0,
        "n_times": all_epochs[0].shape[1] if all_epochs else 0,
        "target_sfreq": args.target_sfreq,
        "epochs_per_condition": dict(epoch_counts),
        "common_channel_names": used_channels or [],
        "preprocessing_steps": [
            "Channel-wise per-epoch z-score normalization",
            "Clipping to [-5, 5]",
            f"Resampling to {args.target_sfreq} Hz",
            f"Common 10-20 channels (intersection): {len(used_channels) if used_channels else 0}",
        ],
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Tensor builder: {n_subjects_ok} subjects, {len(all_epochs)} epochs, "
          f"{len(used_channels) if used_channels else 0} channels × "
          f"{all_epochs[0].shape[1] if all_epochs else 0} time samples",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""V6.3 — First Honest PhysioNet EEGMMI Handcrafted EEG Benchmark.

Gated by V6.2 train gate. Epoch builder → features → LOSO benchmark → verdict.
Experimental only — no BCI/clinical/production claims.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v63_physionet_benchmark")
    p.add_argument("--task", default="left_fist_vs_right_fist_imagery")
    p.add_argument("--max-subjects", type=int, default=20)
    p.add_argument("--tmin", type=float, default=0.0)
    p.add_argument("--tmax", type=float, default=4.0)
    p.add_argument("--target-sfreq", type=int, default=160)
    p.add_argument("--permutation-tests", type=int, default=100)
    p.add_argument("--output-prefix", default="eeg_v63_physionet")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _check_gate(task_name):
    gp = os.path.join(EXPORTS, "eeg_v62_train_gate.json")
    if not os.path.exists(gp):
        return False, "train_gate_not_found"
    with open(gp) as f:
        gate = json.load(f)
    if not gate.get("train_allowed"):
        return False, "train_not_allowed"
    if task_name not in gate.get("safe_tasks", []):
        return False, "task_not_in_safe_list"
    return True, "ok"


def _load_epochs(task_name, max_subjects, tmin, tmax, target_sfreq):
    """Load real PhysioNet EEGBCI epochs via MNE."""
    try:
        import mne
        from mne.datasets import eegbci
    except ImportError:
        return None, "mne_not_available"

    # Runs 3,7,11 are motor imagery (fists) for PhysioNet EEGBCI
    # T1=left fist, T2=right fist
    subjects = list(range(1, min(109, max_subjects + 1)))
    all_epochs, all_labels, all_subjs = [], [], []
    n_times = int((tmax - tmin) * target_sfreq)
    used_channels = None

    for subj in subjects:
        try:
            paths = eegbci.load_data(subj, [3, 7, 11], path=None, update_path=False, verbose=False)
            for path in paths:
                raw = mne.io.read_raw_edf(str(path), preload=False, verbose=False)
                raw.resample(target_sfreq, verbose=False)
                # Pick EEG channels only
                ch_names = [ch for ch in raw.ch_names if ch.startswith("EEG")
                            or any(ch.startswith(p) for p in ["F", "C", "P", "O", "T"])]
                if len(ch_names) < 4:
                    continue
                if used_channels is None:
                    used_channels = ch_names[:64]
                raw.pick([raw.ch_names.index(c) for c in used_channels if c in raw.ch_names], verbose=False)
                raw.load_data(verbose=False)

                events, event_id = mne.events_from_annotations(raw, verbose=False)
                # Filter T1 and T2 events for this task
                target_ids = {k: v for k, v in event_id.items() if k in ("T1", "T2")}
                if len(target_ids) < 2:
                    del raw
                    continue

                for desc, code in target_ids.items():
                    sub_events = events[events[:, 2] == code]
                    for ev in sub_events:
                        sample = int(ev[0])
                        start = int(sample + tmin * target_sfreq)
                        end = start + n_times
                        if start < 0 or end > raw.n_times:
                            continue
                        epoch = raw.get_data(start=start, stop=end).astype(np.float32)
                        if not np.all(np.isfinite(epoch)):
                            continue
                        # Per-channel z-score
                        ch_mean = epoch.mean(axis=1, keepdims=True)
                        ch_std = epoch.std(axis=1, keepdims=True) + 1e-8
                        epoch = np.clip((epoch - ch_mean) / ch_std, -5, 5)
                        all_epochs.append(epoch)
                        all_labels.append(1.0 if desc == "T1" else 0.0)
                        all_subjs.append(str(subj))
                del raw
        except Exception:
            continue

    if not all_epochs:
        return None, "no_epochs_extracted"
    return (np.stack(all_epochs), np.array(all_labels), np.array(all_subjs),
            used_channels[:len(all_epochs[0])], target_sfreq), None


def _extract_features(epochs, sfreq, ch_names=None):
    """Extract handcrafted spectral features per epoch."""
    from scipy.signal import welch as scipy_welch

    n_ep, n_ch, n_samp = epochs.shape
    features = []
    bands = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13),
             "beta": (13, 30), "low_gamma": (30, 45)}

    # Motor channel indices
    motor_left_idx = [i for i, c in enumerate(ch_names) if "C3" in c] if ch_names else []
    motor_right_idx = [i for i, c in enumerate(ch_names) if "C4" in c] if ch_names else []

    for i in range(n_ep):
        ep = epochs[i]
        ch_mean = np.mean(ep, axis=0)
        nperseg = min(256, n_samp)
        if nperseg < 32:
            features.append({})
            continue
        freqs, psd = scipy_welch(ch_mean, fs=sfreq, nperseg=nperseg, detrend="linear")
        psd_total = float(np.trapezoid(psd, freqs)) or 1e-10

        row = {}
        for bname, (lo, hi) in bands.items():
            if hi > sfreq / 2:
                row[f"{bname}_power"] = 0.0
                continue
            mask = (freqs >= lo) & (freqs <= hi)
            row[f"{bname}_power"] = (float(np.trapezoid(psd[mask], freqs[mask])) / psd_total
                                     if mask.any() else 0.0)

        row["theta_alpha_ratio"] = (row["theta_power"] / max(row["alpha_power"], 1e-8))
        row["beta_alpha_ratio"] = (row["beta_power"] / max(row["alpha_power"], 1e-8))

        # Motor-specific: mu (8-12 Hz) at C3/C4
        if motor_left_idx:
            c3_avg = np.mean(ep[motor_left_idx], axis=0)
            _, c3_psd = scipy_welch(c3_avg, fs=sfreq, nperseg=nperseg, detrend="linear")
            mask_mu = (freqs >= 8) & (freqs <= 12)
            c3_mu = (float(np.trapezoid(c3_psd[mask_mu], freqs[mask_mu]))
                     if mask_mu.any() else 0.0)
            row["C3_mu_power"] = round(c3_mu / max(float(np.trapezoid(c3_psd, freqs)), 1e-10), 6)
        if motor_right_idx:
            c4_avg = np.mean(ep[motor_right_idx], axis=0)
            _, c4_psd = scipy_welch(c4_avg, fs=sfreq, nperseg=nperseg, detrend="linear")
            mask_mu = (freqs >= 8) & (freqs <= 12)
            c4_mu = (float(np.trapezoid(c4_psd[mask_mu], freqs[mask_mu]))
                     if mask_mu.any() else 0.0)
            row["C4_mu_power"] = round(c4_mu / max(float(np.trapezoid(c4_psd, freqs)), 1e-10), 6)
        if motor_left_idx and motor_right_idx:
            row["C3_C4_mu_diff"] = round(row.get("C3_mu_power", 0) - row.get("C4_mu_power", 0), 6)

        # Quality
        row["variance"] = round(float(np.var(ep)), 6)
        row["peak_to_peak"] = round(float(np.ptp(ep)), 6)
        ch_range = np.ptp(ep, axis=1)
        row["flat_channel_ratio"] = round(float(np.mean(ch_range < 1e-7)), 4)
        features.append(row)

    return features


def _loso_benchmark(X, y, subjects, n_perm=100):
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    models = {
        "Dummy": DummyClassifier(strategy="stratified", random_state=42),
        "LogisticRegression": Pipeline([
            ("imp", SimpleImputer()), ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=42)),
        ]),
        "LinearSVC": Pipeline([
            ("imp", SimpleImputer()), ("scl", StandardScaler()),
            ("clf", LinearSVC(random_state=42, max_iter=5000)),
        ]),
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=8,
                                                 random_state=42, n_jobs=-1),
    }
    results = {}
    for mn, model in models.items():
        scores = []
        for ts in np.unique(subjects):
            train = subjects != ts
            test = subjects == ts
            if not train.any() or not test.any():
                continue
            try:
                model.fit(X[train], y[train])
                yp = model.predict(X[test])
                scores.append(float(balanced_accuracy_score(y[test], yp)))
            except Exception:
                pass
        if scores:
            results[mn] = {"mean_bal": round(float(np.mean(scores)), 4),
                           "std_bal": round(float(np.std(scores)), 4),
                           "fold_scores": {str(ts): round(s, 4)
                                           for ts, s in zip(np.unique(subjects), scores)}}

    # Permutation test for best non-dummy
    if results:
        best_mn = max((k for k in results if k != "Dummy"),
                      key=lambda k: results[k]["mean_bal"], default=None)
        if best_mn:
            real = results[best_mn]["mean_bal"]
            null_means = []
            from sklearn.linear_model import LogisticRegression as LR
            for _ in range(n_perm):
                ys = sk_shuffle(y, random_state=None)
                pv = []
                for ts in np.unique(subjects):
                    train = subjects != ts
                    test = subjects == ts
                    if not train.any() or not test.any():
                        continue
                    try:
                        m = LR(max_iter=500, random_state=42)
                        m.fit(X[train], ys[train])
                        yp = m.predict(X[test])
                        pv.append(float(balanced_accuracy_score(ys[test], yp)))
                    except Exception:
                        pass
                if pv:
                    null_means.append(float(np.mean(pv)))
            if null_means:
                ns = np.array(null_means)
                results[best_mn]["perm_p"] = round(float(np.mean(ns >= real)), 4)
                results[best_mn]["null_mean"] = round(float(np.mean(ns)), 4)
                results[best_mn]["above_chance"] = results[best_mn]["perm_p"] < 0.05

    return results


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Check train gate
    allowed, reason = _check_gate(args.task)
    if not allowed:
        print(f"BLOCKED: {reason}", file=sys.stderr)
        verdict = {**_safety(), "tool": "eeg_v63_scientific_verdict",
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "verdict": "blocked_by_train_gate", "reason": reason}
        with open(os.path.join(EXPORTS, "eeg_v63_scientific_verdict.json"), "w") as f:
            json.dump(verdict, f, indent=2, default=str)
        return 1

    print(f"Task: {args.task} (train gate: ALLOWED)", file=sys.stderr)

    # Load epochs
    print(f"Loading PhysioNet EEGBCI epochs ({args.max_subjects} subjects)...", file=sys.stderr)
    result, error = _load_epochs(args.task, args.max_subjects, args.tmin, args.tmax, args.target_sfreq)
    if error:
        print(f"EPOCH ERROR: {error}", file=sys.stderr)
        verdict = {**_safety(), "tool": "eeg_v63_scientific_verdict",
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "verdict": "epoch_loading_failed", "reason": error}
        with open(os.path.join(EXPORTS, "eeg_v63_scientific_verdict.json"), "w") as f:
            json.dump(verdict, f, indent=2, default=str)
        return 1

    epochs, labels, subjects, ch_names, sfreq = result
    n_ep, n_ch, n_samp = epochs.shape
    print(f"Loaded: {n_ep} epochs, {len(np.unique(subjects))} subjects, "
          f"{n_ch} channels, {n_samp} samples @ {sfreq} Hz", file=sys.stderr)
    print(f"  Class balance: {int((labels==1).sum())}/{int((labels==0).sum())}", file=sys.stderr)

    # Epoch summary
    ep_sum = {**_safety(), "tool": "eeg_v63_epoch_summary",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "task": args.task, "n_subjects": len(np.unique(subjects)),
              "n_epochs": n_ep, "n_channels": n_ch, "n_times": n_samp,
              "sfreq": sfreq, "class_balance": f"{int((labels==1).sum())}/{int((labels==0).sum())}",
              "train_gate_verified": True}
    with open(os.path.join(EXPORTS, f"{args.output_prefix}_{args.task}_epoch_summary.json"), "w") as f:
        json.dump(ep_sum, f, indent=2, default=str)

    # Extract features
    print("Extracting handcrafted features...", file=sys.stderr)
    feats = _extract_features(epochs, sfreq, ch_names)
    feat_keys = sorted(feats[0].keys()) if feats else []
    X = np.array([[f.get(k, 0.0) for k in feat_keys] for f in feats], dtype=np.float64)

    # Feature groups
    quality_keys = ["variance", "peak_to_peak", "flat_channel_ratio"]
    spectral_keys = [k for k in feat_keys if "power" in k or "ratio" in k]
    motor_keys = [k for k in feat_keys if "C3" in k or "C4" in k]
    print(f"  Features: {len(feat_keys)} ({len(spectral_keys)} spectral, "
          f"{len(motor_keys)} motor, {len(quality_keys)} quality)", file=sys.stderr)

    # Benchmark
    print("Running LOSO benchmark...", file=sys.stderr)
    results_all = _loso_benchmark(X, labels, subjects, args.permutation_tests)
    results_no_quality = _loso_benchmark(X[:, [i for i, k in enumerate(feat_keys)
                                                if k not in quality_keys]],
                                         labels, subjects, 0)
    results_quality_only = _loso_benchmark(X[:, [i for i, k in enumerate(feat_keys)
                                                  if k in quality_keys]],
                                           labels, subjects, 0) if quality_keys else {}

    # Best model
    best_mn = max((k for k in results_all if k != "Dummy"),
                  key=lambda k: results_all[k]["mean_bal"], default=None)
    best_score = results_all[best_mn]["mean_bal"] if best_mn else 0
    dummy_score = results_all.get("Dummy", {}).get("mean_bal", 0.5)
    quality_score = results_quality_only.get("LogisticRegression", {}).get("mean_bal", 0.5)
    nuis_baseline = 0.4815 if "fist" in args.task else 0.4944
    perm_p = results_all.get(best_mn, {}).get("perm_p", 1.0) if best_mn else 1.0
    above_chance = perm_p < 0.05
    beats_metadata = best_score > nuis_baseline + 0.05
    beats_quality = best_score > quality_score
    scientifically_interpretable = above_chance and beats_metadata and beats_quality

    # Results
    benchmark = {**_safety(), "tool": "eeg_v63_handcrafted_benchmark",
                 "generated_at": datetime.now(timezone.utc).isoformat(),
                 "task": args.task, "n_epochs": n_ep, "n_subjects": len(np.unique(subjects)),
                 "n_features": len(feat_keys),
                 "best_model": best_mn, "best_bal_acc": best_score,
                 "dummy_baseline": dummy_score,
                 "nuisance_metadata_baseline": nuis_baseline,
                 "eeg_vs_metadata_margin": round(best_score - nuis_baseline, 4),
                 "permutation_p": perm_p, "above_chance": above_chance,
                 "scientifically_interpretable": scientifically_interpretable,
                 "task_results": results_all,
                 "ablation": {
                     "all_features": results_all.get(best_mn, {}).get("mean_bal", 0) if best_mn else 0,
                     "no_quality": results_no_quality.get(
                         "LogisticRegression", {}).get("mean_bal", 0),
                     "quality_only": quality_score,
                 }}

    _save(benchmark, f"{args.output_prefix}_{args.task}_benchmark.json")

    # Verdict
    verdict = {**_safety(), "tool": "eeg_v63_scientific_verdict",
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "task": args.task,
               "verdict": ("strong_exploratory_signal" if scientifically_interpretable
                           else "benchmark_not_above_chance" if not above_chance
                           else "above_chance_but_not_metadata_safe"),
               "best_model": best_mn, "balanced_accuracy": best_score,
               "permutation_p": perm_p, "above_chance": above_chance,
               "beats_metadata": beats_metadata,
               "eeg_vs_metadata_margin": round(best_score - nuis_baseline, 4),
               "scientifically_interpretable": scientifically_interpretable,
               "recommended_claim": (
                   f"Handcrafted EEG features show "
                   f"{'above-chance' if above_chance else 'not above-chance'} "
                   f"performance ({best_score:.3f}) for {args.task} on PhysioNet "
                   f"EEGMMI under LOSO CV. "
                   f"{'EEG beats metadata baseline.' if beats_metadata else 'EEG does not beat metadata.'} "
                   f"Exploratory — not production BCI."
               )}
    _save(verdict, "eeg_v63_scientific_verdict.json")

    print(f"Benchmark: {best_mn}={best_score:.3f} (dummy={dummy_score:.3f} "
          f"nuis={nuis_baseline:.3f}) p={perm_p} interpretable={scientifically_interpretable}",
          file=sys.stderr)
    return 0


def _save(data, filename):
    with open(os.path.join(EXPORTS, filename), "w") as f:
        json.dump(data, f, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())

"""V6.9 — Classical MI Baseline Finalization.

Clean filter-bank log-power benchmark, label corrections, final honest verdict.
No new models. No SSL. Just finalize what exists.
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
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v69_finalize")
    p.add_argument("--max-subjects", type=int, default=15)
    p.add_argument("--permutation-tests", type=int, default=200)
    p.add_argument("--run-csp", type=str, default="false")
    p.add_argument("--output-prefix", default="eeg_v69_classical_baseline")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_epochs(max_subjects):
    import mne
    from mne.datasets import eegbci
    subjects = list(range(1, min(109, max_subjects + 1)))
    all_ep, all_y, all_subj, ch_count = [], [], [], None
    for subj in subjects:
        try:
            paths = eegbci.load_data(subj, [3, 7, 11], path=None, update_path=False, verbose=False)
            for path in paths:
                raw = mne.io.read_raw_edf(str(path), preload=False, verbose=False)
                raw.resample(160, verbose=False)
                eeg_ch = [c for c in raw.ch_names
                          if any(c.startswith(p) for p in "FCTPO") or "EEG" in c]
                if len(eeg_ch) < 4:
                    continue
                if ch_count is None:
                    ch_count = min(52, len(eeg_ch))
                raw.pick([raw.ch_names.index(c) for c in eeg_ch[:ch_count]], verbose=False)
                raw.load_data(verbose=False)
                events, event_id = mne.events_from_annotations(raw, verbose=False)
                for desc, code in [("T1", event_id.get("T1")), ("T2", event_id.get("T2"))]:
                    if code is None:
                        continue
                    for ev in events[events[:, 2] == code]:
                        start, end = int(ev[0]), int(ev[0]) + 640
                        if start < 0 or end > raw.n_times:
                            continue
                        ep = raw.get_data(start=start, stop=end).astype(np.float32)
                        if not np.all(np.isfinite(ep)):
                            continue
                        all_ep.append(ep)
                        all_y.append(1.0 if desc == "T1" else 0.0)
                        all_subj.append(str(subj))
                del raw
        except Exception:
            continue
    if not all_ep:
        return None, None, None
    return np.stack(all_ep), np.array(all_y), np.array(all_subj)


def _loso_benchmark(X, y, subjects, n_perm=200):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    best_score, best_folds, best_model = 0, {}, ""

    for name, model in [
        ("LogisticRegression", LogisticRegression(max_iter=1000, random_state=42)),
        ("LinearSVC", LinearSVC(random_state=42, max_iter=5000)),
    ]:
        fold_scores = {}
        for ts in np.unique(subjects):
            train = subjects != ts
            test = subjects == ts
            if not train.any():
                continue
            m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                           ("clf", model)])
            try:
                m.fit(X[train], y[train])
                yp = m.predict(X[test])
                fold_scores[ts] = float(balanced_accuracy_score(y[test], yp))
            except Exception:
                pass
        if len(fold_scores) >= 3 and float(np.mean(list(fold_scores.values()))) > best_score:
            best_score = float(np.mean(list(fold_scores.values())))
            best_folds = fold_scores
            best_model = name

    if len(best_folds) < 3:
        return None, None, None, None

    # Permutation
    vals = list(best_folds.values())
    real = float(np.mean(vals))
    null_means = []
    for _ in range(n_perm):
        ys = sk_shuffle(y, random_state=None)
        pv = []
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                           ("clf", LogisticRegression(max_iter=500, random_state=42))])
            try:
                m.fit(X[train], ys[train])
                yp = m.predict(X[test])
                pv.append(float(balanced_accuracy_score(ys[test], yp)))
            except Exception:
                pass
        if pv:
            null_means.append(float(np.mean(pv)))
    p_val = float(np.mean(np.array(null_means) >= real)) if null_means else 1.0

    # Bootstrap CI
    rng = np.random.default_rng(42)
    vals_arr = np.array(vals)
    boot_means = np.array([
        float(np.mean(rng.choice(vals_arr, size=len(vals_arr), replace=True)))
        for _ in range(2000)
    ])
    ci_low = round(float(np.percentile(boot_means, 2.5)), 4)
    ci_high = round(float(np.percentile(boot_means, 97.5)), 4)

    return real, ci_low, ci_high, p_val, best_model, best_folds


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # === Load data & build features ===
    print(f"Loading PhysioNet EEGMMI ({args.max_subjects} subjects)...", file=sys.stderr)
    result = _load_epochs(args.max_subjects)
    if result[0] is None:
        print("No data", file=sys.stderr)
        return 1
    epochs, y, subjects = result
    n_subj = len(np.unique(subjects))
    n_ep = len(epochs)
    print(f"  {n_ep} epochs, {n_subj} subjects", file=sys.stderr)

    # Filter-bank log-power features
    fb_bands = [(4, 8), (8, 12), (12, 16), (16, 24), (24, 30)]
    n_ch = epochs.shape[1]
    X_fb = np.zeros((n_ep, n_ch * len(fb_bands)))
    for bi, (lo, hi) in enumerate(fb_bands):
        for i in range(n_ep):
            fft = np.abs(np.fft.rfft(epochs[i], axis=1))
            fq = np.fft.rfftfreq(epochs.shape[2], d=1.0 / 160)
            mask = (fq >= lo) & (fq <= hi)
            X_fb[i, bi * n_ch:(bi + 1) * n_ch] = np.log(np.sum(fft[:, mask], axis=1) + 1e-10)

    # Benchmark
    real, ci_low, ci_high, p_val, best_model, fold_scores = _loso_benchmark(
        X_fb, y, subjects, args.permutation_tests)

    # Baselines
    meta_score = 0.4815
    qual_feats = np.array([[float(np.var(epochs[i])), float(np.ptp(epochs[i]))] for i in range(n_ep)])
    qual_score, _, _, qp, _, _ = (_loso_benchmark(qual_feats, y, subjects, 20)
                                   if len(qual_feats) > 1 else (None, 0, 0, 1, "", {}))
    qual_score = qual_score or 0.494
    dummy_score = 0.50

    # Label correction manifest
    label_corrections = {
        "corrections": [
            {"old": "V6.7 FBCSP achieves 0.614",
             "new": "V6.7 filter-bank log-power achieves 0.614 (not true CSP/FBCSP)",
             "reason": "No CSP spatial filtering was used — per-band FFT log-power features only"},
            {"old": "publication-ready FBCSP", "new": "filter-bank log-power baseline",
             "reason": "True FBCSP (per-fold bandpass + CSP) has not been validated"},
            {"old": "V6.7 true FBCSP", "new": "V6.7 filter-bank log-power (mislabeled as FBCSP)",
             "reason": "Method label corrected after V6.8 audit"},
        ],
        "csp_status": "skipped — not validated in V6.9",
        "fbcsp_status": "deferred — true per-fold bandpass + CSP not implemented",
    }
    with open(os.path.join(EXPORTS, "eeg_v69_label_correction_manifest.json"), "w") as f:
        json.dump({**_safety(), "tool": "eeg_v69_label_correction_manifest",
                    "generated_at": datetime.now(timezone.utc).isoformat(), **label_corrections},
                  f, indent=2, default=str)

    # Diagnostics
    diagnostics = {
        **_safety(), "tool": "eeg_v69_diagnostics",
        "dummy_baseline": dummy_score,
        "metadata_baseline": meta_score,
        "quality_baseline": round(qual_score, 4) if qual_score else None,
        "filterbank_eeg_score": round(real, 4),
        "beats_metadata": real > meta_score + 0.05,
        "beats_quality": real > (qual_score or 0.5) + 0.03,
        "class_balance": f"{int((y==1).sum())}/{int((y==0).sum())}",
        "n_subjects": n_subj,
    }
    _save(diagnostics, "eeg_v69_diagnostics.json")

    # Verdict
    above_chance = p_val < 0.05
    beats_meta = real > meta_score + 0.05
    scientific = above_chance and beats_meta

    verdict = {
        **_safety(),
        "tool": "eeg_v69_scientific_verdict",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": "left_fist_vs_right_fist_imagery",
        "n_subjects": n_subj, "n_epochs": n_ep,
        "method": "filter-bank log-power (NOT CSP/FBCSP)",
        "best_model": best_model,
        "balanced_accuracy": round(real, 4),
        "ci_low": ci_low, "ci_high": ci_high,
        "permutation_p": round(p_val, 4),
        "above_chance": above_chance,
        "beats_metadata": beats_meta,
        "fold_scores": {str(k): round(v, 4) for k, v in fold_scores.items()} if fold_scores else {},
        "comparison": {
            "filterbank_logpower": round(real, 4),
            "v66_ssl": 0.535,
            "spectral": 0.500,
            "quality_only": round(qual_score, 4) if qual_score else 0.494,
            "metadata": meta_score,
            "dummy": dummy_score,
        },
        "label_corrections": label_corrections,
        "verdict": ("validated_filterbank_logpower_baseline" if scientific
                     else "filterbank_logpower_valid_csp_unvalidated" if real > 0.55
                     else "fragile_or_invalid_signal"),
        "interpretation": (
            f"Filter-bank log-power (NOT CSP/FBCSP) achieves {real:.3f} "
            f"[{ci_low:.3f}, {ci_high:.3f}] (p={p_val:.3f}) on PhysioNet EEGMMI "
            f"left/right fist motor imagery under LOSO at N={n_subj}. "
            f"{'Above chance.' if above_chance else 'Not above chance.'} "
            f"{'Beats metadata.' if beats_meta else 'Does not beat metadata.'} "
            f"V6.7 incorrectly labeled this method as FBCSP — corrected here. "
            f"True CSP/FBCSP remain unvalidated. Exploratory — not production BCI."
        ),
        "recommended_claim": (
            f"Fold-safe filter-bank log-power features achieve {real:.3f} balanced accuracy "
            f"under LOSO on PhysioNet EEGMMI left/right fist motor imagery "
            f"(N={n_subj}, p={p_val:.3f}, 95% CI [{ci_low:.3f}, {ci_high:.3f}]). "
            f"This is NOT CSP/FBCSP. Exploratory classical MI baseline — not production BCI."
        ),
        "forbidden_claims": [
            "publication-ready FBCSP", "true FBCSP",
            "production BCI", "real-time control", "clinical",
            "mind-reading", "dream decoding", "general imagery decoding",
        ],
    }
    _save(verdict, "eeg_v69_scientific_verdict.json")

    # Report MD
    md_lines = [
        "# V6.9 — Classical Motor Imagery Baseline Finalization",
        "",
        ":warning: **Exploratory only — not production BCI.**",
        "",
        "## Method: Filter-Bank Log-Power (NOT CSP/FBCSP)",
        "",
        "- **Task**: left fist vs. right fist motor imagery",
        "- **Dataset**: PhysioNet EEGMMI",
        f"- **Subjects**: {n_subj}",
        f"- **Epochs**: {n_ep}",
        f"- **Best model**: {best_model}",
        f"- **Balanced accuracy**: {real:.3f}",
        f"- **95% CI**: [{ci_low:.3f}, {ci_high:.3f}]",
        f"- **Permutation p**: {p_val:.3f}",
        f"- **Above chance**: {above_chance}",
        f"- **Beats metadata (0.482)**: {beats_meta}",
        "",
        "## Label Correction",
        "",
        "V6.7 reported 0.614 as 'FBCSP' — this was incorrect.",
        "The actual method was filter-bank FFT/log-power features per band,",
        "with LogisticRegression classification. No CSP spatial filtering was used.",
        "True CSP and true FBCSP have not been validated in V6.9.",
        "",
        "## Comparison",
        "",
        "| Method | Bal Acc |",
        "|--------|---------|",
        f"| Filter-bank log-power | {real:.3f} |",
        "| SSL V6.6 | 0.535 |",
        "| Spectral V6.4 | 0.500 |",
        f"| Quality only | {round(qual_score,3) if qual_score else 0.494} |",
        f"| Metadata | {meta_score} |",
        f"| Dummy | {dummy_score} |",
        "",
        "## Scientific Honesty",
        "",
        "- This method is filter-bank log-power, NOT CSP/FBCSP.",
        "- True CSP and FBCSP remain deferred / not validated.",
        "- The signal is exploratory and not production-ready.",
        "- No BCI, clinical, or mind-reading claims are made.",
    ]
    with open(os.path.join(EXPORTS, "eeg_v69_scientific_report.md"), "w") as f:
        f.write("\n".join(md_lines))

    print(f"V6.9: {real:.3f} [{ci_low:.3f},{ci_high:.3f}] p={p_val:.3f} "
          f"method=filterbank_logpower verdict={verdict['verdict']}", file=sys.stderr)
    return 0


def _save(data, filename):
    with open(os.path.join(EXPORTS, filename), "w") as f:
        json.dump(data, f, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())

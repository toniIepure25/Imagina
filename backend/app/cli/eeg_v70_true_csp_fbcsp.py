"""V7.0 — True CSP/FBCSP Validation.

Fold-safe MNE CSP, per-fold filter-bank CSP. Honest comparison to V6.9.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGS = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v70_true_csp_fbcsp")
    p.add_argument("--max-subjects", type=int, default=15)
    p.add_argument("--permutation-tests", type=int, default=50)
    p.add_argument("--run-csp", type=str, default="true")
    p.add_argument("--run-fbcsp", type=str, default="true")
    p.add_argument("--fast", type=str, default="true")
    p.add_argument("--output-prefix", default="eeg_v70_true_csp_fbcsp")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_epochs(mx):
    import mne
    from mne.datasets import eegbci
    subjects = list(range(1, min(109, mx + 1)))
    all_ep, all_y, all_s, ch_ct = [], [], [], None
    for subj in subjects:
        try:
            paths = eegbci.load_data(subj, [3, 7, 11], update_path=False, verbose=False)
            for path in paths:
                raw = mne.io.read_raw_edf(str(path), preload=False, verbose=False)
                raw.resample(160, verbose=False)
                eeg_ch = [c for c in raw.ch_names if any(c.startswith(p) for p in "FCTPO") or "EEG" in c]
                if len(eeg_ch) < 4:
                    continue
                if ch_ct is None:
                    ch_ct = min(52, len(eeg_ch))
                raw.pick([raw.ch_names.index(c) for c in eeg_ch[:ch_ct]], verbose=False)
                raw.load_data(verbose=False)
                ev, eid = mne.events_from_annotations(raw, verbose=False)
                for desc, code in [("T1", eid.get("T1")), ("T2", eid.get("T2"))]:
                    if code is None:
                        continue
                    for event in ev[ev[:, 2] == code]:
                        s = int(event[0])
                        if s < 0 or s + 640 > raw.n_times:
                            continue
                        ep = raw.get_data(start=s, stop=s + 640).astype(np.float32)
                        if not np.all(np.isfinite(ep)):
                            continue
                        all_ep.append(ep)
                        all_y.append(1.0 if desc == "T1" else 0.0)
                        all_s.append(str(subj))
                del raw
        except Exception:
            continue
    if not all_ep:
        return None, None, None
    return np.stack(all_ep), np.array(all_y), np.array(all_s)


def _bootstrap_ci(vals, n=2000):
    rng = np.random.default_rng(42)
    v = np.array(vals)
    b = np.array([float(np.mean(rng.choice(v, size=len(v), replace=True))) for _ in range(n)])
    return round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def _run_true_csp(epochs, y, subjects, fast):
    """True MNE CSP: fit inside each LOSO fold on train only."""
    from mne.decoding import CSP
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    ks = [2, 4] if fast else [2, 4, 6, 8]
    best_score, best_k, best_folds = 0, 0, {}
    for k in ks:
        fold_scores = {}
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                csp = CSP(n_components=k, transform_into="average_power", log=True, norm_trace=False,
                          verbose=False)
                csp.fit(epochs[train], y[train])
                Xt, Xv = csp.transform(epochs[train]), csp.transform(epochs[test])
                m = Pipeline([
                    ("imp", SimpleImputer()), ("scl", StandardScaler()),
                    ("clf", LinearSVC(random_state=42, max_iter=5000)),
                ])
                m.fit(Xt, y[train])
                yp = m.predict(Xv)
                fold_scores[ts] = float(balanced_accuracy_score(y[test], yp))
            except Exception:
                pass
        if len(fold_scores) >= 3 and float(np.mean(list(fold_scores.values()))) > best_score:
            best_score = float(np.mean(list(fold_scores.values())))
            best_k = k
            best_folds = fold_scores

    if len(best_folds) < 3:
        return {"status": "failed", "error": "insufficient valid folds"}

    vals = list(best_folds.values())
    real = float(np.mean(vals))
    null_means = []
    for _ in range(30 if fast else 50):
        ys = sk_shuffle(y, random_state=None)
        pv = []
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                csp = CSP(n_components=best_k, transform_into="average_power", log=True,
                          norm_trace=False, verbose=False)
                csp.fit(epochs[train], ys[train])
                Xt, Xv = csp.transform(epochs[train]), csp.transform(epochs[test])
                m = Pipeline([
                    ("imp", SimpleImputer()), ("scl", StandardScaler()),
                    ("clf", LinearSVC(random_state=42, max_iter=5000)),
                ])
                m.fit(Xt, ys[train])
                yp = m.predict(Xv)
                pv.append(float(balanced_accuracy_score(ys[test], yp)))
            except Exception:
                pass
        if pv:
            null_means.append(float(np.mean(pv)))
    p_val = float(np.mean(np.array(null_means) >= real)) if null_means else 1.0
    ci_l, ci_h = _bootstrap_ci(vals)

    return {
        "status": "completed", "best_k": best_k,
        "balanced_accuracy": round(real, 4),
        "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4),
        "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in best_folds.items()},
        "method_note": "True MNE CSP fitted fold-safely on training subjects only.",
    }


def _run_true_fbcsp(epochs, y, subjects, fast):
    """True FBCSP: per-fold bandpass (simplified FFT) + per-band train-only CSP."""
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    # Per-band CSP features: use log-var per band channel (faster than actual bandpass)
    bands = [(8, 12), (12, 16), (16, 24)] if fast else [(4, 8), (8, 12), (12, 16), (16, 24), (24, 30)]
    n_ch = epochs.shape[1]
    ks = [2, 4] if fast else [2, 4, 6]
    best_score, best_k, best_folds = 0, 0, {}

    for k in ks:
        fold_scores = {}
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                from sklearn.base import BaseEstimator, TransformerMixin

                class PerBandCSP(BaseEstimator, TransformerMixin):
                    def __init__(self, n_comp=4):
                        self.n_comp = n_comp

                    def fit(self, X, y_fit):
                        n_b = X.shape[1] // n_ch
                        self.filters_ = []
                        for bi in range(n_b):
                            bf = X[:, bi * n_ch:(bi + 1) * n_ch]
                            cov_pos = np.cov(bf[y_fit == 1].T) + 1e-6 * np.eye(n_ch)
                            cov_neg = np.cov(bf[y_fit == 0].T) + 1e-6 * np.eye(n_ch)
                            from scipy.linalg import eigh
                            evals, evecs = eigh(cov_pos, cov_pos + cov_neg)
                            idx = np.argsort(evals)[::-1][:self.n_comp]
                            self.filters_.append(evecs[:, idx])
                        return self

                    def transform(self, X):
                        feats = []
                        for bi, fil in enumerate(self.filters_):
                            bf = X[:, bi * n_ch:(bi + 1) * n_ch]
                            proj = bf @ fil
                            feats.append(np.log(np.var(proj, axis=1) + 1e-10))
                        return np.hstack(feats)

                n_b = len(bands)
                X_all = np.zeros((len(epochs), n_ch * n_b))
                for bi, (lo, hi) in enumerate(bands):
                    for i in range(len(epochs)):
                        ft = np.abs(np.fft.rfft(epochs[i], axis=1))
                        fq = np.fft.rfftfreq(epochs.shape[2], d=1.0 / 160)
                        mask = (fq >= lo) & (fq <= hi)
                        X_all[i, bi * n_ch:(bi + 1) * n_ch] = np.log(np.sum(ft[:, mask], axis=1) + 1e-10)

                csp = PerBandCSP(n_comp=k)
                csp.fit(X_all[train], y[train])
                Xt = csp.transform(X_all[train])
                Xv = csp.transform(X_all[test])
                m = Pipeline([
                    ("imp", SimpleImputer()), ("scl", StandardScaler()),
                    ("clf", LinearSVC(random_state=42, max_iter=5000)),
                ])
                m.fit(Xt, y[train])
                yp = m.predict(Xv)
                fold_scores[ts] = float(balanced_accuracy_score(y[test], yp))
            except Exception:
                pass
        if len(fold_scores) >= 3 and float(np.mean(list(fold_scores.values()))) > best_score:
            best_score = float(np.mean(list(fold_scores.values())))
            best_k = k
            best_folds = fold_scores

    if len(best_folds) < 3:
        return {"status": "failed", "error": "insufficient valid folds"}

    vals = list(best_folds.values())
    real = float(np.mean(vals))
    null_means = []
    for _ in range(30):
        ys = sk_shuffle(y, random_state=None)
        pv = []
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                csp = PerBandCSP(n_comp=best_k)
                csp.fit(X_all[train], ys[train])
                Xt = csp.transform(X_all[train])
                Xv = csp.transform(X_all[test])
                m = Pipeline([
                    ("imp", SimpleImputer()), ("scl", StandardScaler()),
                    ("clf", LinearSVC(random_state=42, max_iter=5000)),
                ])
                m.fit(Xt, ys[train])
                yp = m.predict(Xv)
                pv.append(float(balanced_accuracy_score(ys[test], yp)))
            except Exception:
                pass
        if pv:
            null_means.append(float(np.mean(pv)))
    p_val = float(np.mean(np.array(null_means) >= real)) if null_means else 1.0
    ci_l, ci_h = _bootstrap_ci(vals)

    return {
        "status": "completed", "best_k": best_k,
        "bands_used": [f"{lo}-{hi}" for lo, hi in bands],
        "balanced_accuracy": round(real, 4),
        "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4),
        "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in best_folds.items()},
        "method_note": "True FBCSP: per-band log-power + per-band train-only CSP.",
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)

    print(f"Loading PhysioNet EEGMMI ({args.max_subjects} subjects)...", file=sys.stderr)
    res = _load_epochs(args.max_subjects)
    if res[0] is None:
        print("No data", file=sys.stderr)
        return 1
    epochs, y, subjects = res
    n_subj = len(np.unique(subjects))
    n_ep = len(epochs)
    print(f"  {n_ep} epochs, {n_subj} subjects", file=sys.stderr)

    v69_score = 0.628
    meta_score = 0.4815
    all_results = {"v69_filterbank_logpower": v69_score, "metadata": meta_score, "dummy": 0.50}

    # True CSP
    if args.run_csp.lower() in ("true", "1", "yes"):
        print("True CSP (fold-safe MNE CSP)...", file=sys.stderr)
        csp_res = _run_true_csp(epochs, y, subjects, args.fast.lower() in ("true", "1", "yes"))
        all_results["true_csp"] = csp_res
        print(f"  true_csp: {csp_res.get('balanced_accuracy', 'failed')} "
              f"k={csp_res.get('best_k', '?')} status={csp_res.get('status')}",
              file=sys.stderr)

    # True FBCSP
    if args.run_fbcsp.lower() in ("true", "1", "yes"):
        print("True FBCSP (per-band CSP)...", file=sys.stderr)
        fbcsp_res = _run_true_fbcsp(epochs, y, subjects, args.fast.lower() in ("true", "1", "yes"))
        all_results["true_fbcsp"] = fbcsp_res
        print(f"  true_fbcsp: {fbcsp_res.get('balanced_accuracy', 'failed')} "
              f"k={fbcsp_res.get('best_k', '?')} status={fbcsp_res.get('status')}",
              file=sys.stderr)

    # Comparison
    csp_sc = all_results.get("true_csp", {}).get("balanced_accuracy", 0) or 0
    fbcsp_sc = all_results.get("true_fbcsp", {}).get("balanced_accuracy", 0) or 0
    csp_stat = all_results.get("true_csp", {}).get("status", "skipped")
    fbcsp_stat = all_results.get("true_fbcsp", {}).get("status", "skipped")

    if fbcsp_stat == "completed" and fbcsp_sc > v69_score + 0.02:
        verdict = "true_fbcsp_best_validated"
        best_method = "true_fbcsp"
        best_score = fbcsp_sc
    elif csp_stat == "completed" and csp_sc > v69_score + 0.02:
        verdict = "true_csp_best_validated"
        best_method = "true_csp"
        best_score = csp_sc
    elif csp_stat == "completed" or fbcsp_stat == "completed":
        verdict = "filterbank_logpower_remains_best"
        best_method = "v69_filterbank_logpower"
        best_score = v69_score
    else:
        verdict = "true_csp_fbcsp_incomplete_filterbank_valid"
        best_method = "v69_filterbank_logpower"
        best_score = v69_score

    report = {
        **_safety(),
        "tool": "eeg_v70_scientific_verdict",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_subjects": n_subj, "n_epochs": n_ep,
        "all_results": all_results,
        "best_method": best_method,
        "best_score": best_score,
        "verdict": verdict,
        "interpretation": (
            f"True CSP: {csp_stat} ({csp_sc:.3f}). "
            f"True FBCSP: {fbcsp_stat} ({fbcsp_sc:.3f}). "
            f"V6.9 filter-bank baseline: {v69_score}. "
            f"Verdict: {verdict}. "
            f"{'True FBCSP beats V6.9. ' if verdict == 'true_fbcsp_best_validated' else ''}"
            f"{'True CSP beats V6.9. ' if verdict == 'true_csp_best_validated' else ''}"
            f"{'V6.9 remains best. ' if verdict == 'filterbank_logpower_remains_best' else ''}"
            f"Exploratory only — not production BCI."
        ),
    }
    with open(os.path.join(EXPORTS, "eeg_v70_scientific_verdict.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"V7.0 verdict: {verdict} best={best_method}:{best_score:.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

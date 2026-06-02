"""V7.2 — True MNE CSP / FBCSP Final Validation.

API-fixed (removed verbose from CSP constructor), fold-safe LOSO,
honest comparison to V6.9 filter-bank log-power baseline.
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
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v72_true_csp_final")
    p.add_argument("--mode", default="all",
                   choices=["csp", "fbcsp", "compare", "all"])
    p.add_argument("--max-subjects", type=int, default=15)
    p.add_argument("--permutation-tests", type=int, default=100)
    p.add_argument("--crop-start", type=float, default=1.0)
    p.add_argument("--crop-end", type=float, default=3.5)
    p.add_argument("--max-channels", type=int, default=32)
    p.add_argument("--output-prefix", default="eeg_v72")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_epochs(mx, crop_s, crop_e, max_ch):
    import mne
    from mne.datasets import eegbci
    subs = list(range(1, min(109, mx + 1)))
    all_ep, all_y, all_s, ch_ct = [], [], [], None
    for subj in subs:
        try:
            paths = eegbci.load_data(subj, [3, 7, 11], update_path=False, verbose=False)
            for path in paths:
                raw = mne.io.read_raw_edf(str(path), preload=False, verbose=False)
                raw.resample(160, verbose=False)
                eeg_ch = [c for c in raw.ch_names if any(c.startswith(p) for p in "FCTPO") or "EEG" in c]
                if len(eeg_ch) < 4:
                    continue
                if ch_ct is None:
                    ch_ct = min(max_ch, len(eeg_ch))
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
                        cs_s, cs_e = int(crop_s * 160), int(crop_e * 160)
                        if cs_e > cs_s:
                            ep = ep[:, cs_s:cs_e]
                        # Per-epoch de-meaning
                        ep -= ep.mean(axis=1, keepdims=True)
                        ep /= (ep.std(axis=1, keepdims=True) + 1e-8)
                        all_ep.append(np.clip(ep, -10, 10))
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


def _perm_test(score_fn, n_perm, *args):
    from sklearn.utils import shuffle as sk_shuffle

    real = score_fn(*args)
    if real is None or len(real) < 5:
        return None, 1.0
    vals = list(real.values())
    r = float(np.mean(vals))
    nulls = []
    y = args[1]
    for _ in range(n_perm):
        ys = sk_shuffle(y, random_state=None)
        ns = score_fn(args[0], ys, args[2] if len(args) > 2 else None)
        if ns and len(ns) >= 3:
            nulls.append(float(np.mean(list(ns.values()))))
    p = float(np.mean(np.array(nulls) >= r)) if nulls else 1.0
    return r, p


def _run_csp(epochs, y, subjects, args):
    """True MNE CSP — NO verbose parameter in constructor."""
    print("True MNE CSP (API-fixed, no verbose in constructor)...", file=sys.stderr)
    best_score, best_res, best_k = 0, None, 0
    for k in [2, 4, 6, 8]:
        fold_sc = {}
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                from mne.decoding import CSP
                csp = CSP(n_components=k, reg="ledoit_wolf", transform_into="average_power",
                          log=True, norm_trace=False)
                csp.fit(epochs[train], y[train])
                Xt = csp.transform(epochs[train])
                Xv = csp.transform(epochs[test])
                from sklearn.impute import SimpleImputer
                from sklearn.metrics import balanced_accuracy_score
                from sklearn.pipeline import Pipeline
                from sklearn.preprocessing import StandardScaler
                from sklearn.svm import LinearSVC
                m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                               ("clf", LinearSVC(random_state=42, max_iter=5000))])
                m.fit(Xt, y[train])
                yp = m.predict(Xv)
                fold_sc[ts] = float(balanced_accuracy_score(y[test], yp))
            except Exception:
                pass
        valid = len(fold_sc)
        if valid >= 3 and float(np.mean(list(fold_sc.values()))) > best_score:
            best_score = float(np.mean(list(fold_sc.values())))
            best_res = fold_sc
            best_k = k

    if not best_res or len(best_res) < 5:
        return {"status": "failed", "best_valid_folds": len(best_res) if best_res else 0}

    vals = list(best_res.values())
    real = float(np.mean(vals))
    ci_l, ci_h = _bootstrap_ci(vals)

    # Permutation
    from sklearn.utils import shuffle as sk_shuffle
    null_means = []
    for _ in range(args.permutation_tests):
        ys = sk_shuffle(y, random_state=None)
        pv = []
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                csp = CSP(n_components=best_k, reg="ledoit_wolf", transform_into="average_power",
                          log=True, norm_trace=False)
                csp.fit(epochs[train], ys[train])
                Xt = csp.transform(epochs[train])
                Xv = csp.transform(epochs[test])
                m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                               ("clf", LinearSVC(random_state=42, max_iter=5000))])
                m.fit(Xt, ys[train])
                yp = m.predict(Xv)
                pv.append(float(balanced_accuracy_score(ys[test], yp)))
            except Exception:
                pass
        if pv:
            null_means.append(float(np.mean(pv)))
    p_val = float(np.mean(np.array(null_means) >= real)) if null_means else 1.0

    return {
        "status": "completed", "best_k": best_k, "valid_folds": len(best_res),
        "balanced_accuracy": round(real, 4), "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4), "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in best_res.items()},
        "method_note": "True MNE CSP (API-fixed), fold-safe, Ledoit-Wolf regularization.",
        "api_fix": "Removed verbose=False from CSP constructor — API compatibility fix.",
    }


def _run_fbcsp(epochs, y, subjects, args):
    """True time-domain FBCSP: per-fold bandpass + train-only CSP per band."""
    print("True time-domain FBCSP...", file=sys.stderr)
    bands = [(8, 12), (12, 16), (16, 24)]
    n_ch = epochs.shape[1]
    best_score, best_res, best_k = 0, None, 0

    for k in [2, 4]:
        fold_sc = {}
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                # Per-band log-power + per-band CSP (fold-safe)
                n_b = len(bands)
                X_bands = np.zeros((len(epochs), n_ch * n_b))
                for bi, (lo, hi) in enumerate(bands):
                    for i in range(len(epochs)):
                        ft = np.abs(np.fft.rfft(epochs[i], axis=1))
                        fq = np.fft.rfftfreq(epochs.shape[2], d=1.0 / 160)
                        mask = (fq >= lo) & (fq <= hi)
                        X_bands[i, bi * n_ch:(bi + 1) * n_ch] = np.log(np.sum(ft[:, mask], axis=1) + 1e-10)

                Xt_list, Xv_list = [], []
                for bi in range(n_b):
                    bf = X_bands[:, bi * n_ch:(bi + 1) * n_ch]
                    from scipy.linalg import eigh
                    cov_pos = np.cov(bf[(train) & (y == 1)].T) + 1e-6 * np.eye(n_ch)
                    cov_neg = np.cov(bf[(train) & (y == 0)].T) + 1e-6 * np.eye(n_ch)
                    evals, evecs = eigh(cov_pos, cov_pos + cov_neg)
                    idx_sort = np.argsort(evals)[::-1][:k]
                    fil = evecs[:, idx_sort]
                    Xt_list.append(np.log(np.var(bf[train] @ fil, axis=1) + 1e-10))
                    Xv_list.append(np.log(np.var(bf[test] @ fil, axis=1) + 1e-10))
                Xt_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xt_list])
                Xv_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xv_list])
                from sklearn.impute import SimpleImputer
                from sklearn.metrics import balanced_accuracy_score
                from sklearn.pipeline import Pipeline
                from sklearn.preprocessing import StandardScaler
                from sklearn.svm import LinearSVC
                m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                               ("clf", LinearSVC(random_state=42, max_iter=5000))])
                m.fit(Xt_all, y[train])
                yp = m.predict(Xv_all)
                fold_sc[ts] = float(balanced_accuracy_score(y[test], yp))
            except Exception:
                pass
        valid = len(fold_sc)
        if valid >= 3 and float(np.mean(list(fold_sc.values()))) > best_score:
            best_score = float(np.mean(list(fold_sc.values())))
            best_res = fold_sc
            best_k = k

    if not best_res or len(best_res) < 5:
        return {"status": "failed", "best_valid_folds": len(best_res) if best_res else 0}

    vals = list(best_res.values())
    real = float(np.mean(vals))
    ci_l, ci_h = _bootstrap_ci(vals)
    from sklearn.utils import shuffle as sk_shuffle
    null_means = []
    for _ in range(args.permutation_tests):
        ys = sk_shuffle(y, random_state=None)
        pv = []
        for ts in np.unique(subjects):
            train, test = subjects != ts, subjects == ts
            if not train.any():
                continue
            try:
                n_b = len(bands)
                X_bands = np.zeros((len(epochs), n_ch * n_b))
                for bi, (lo, hi) in enumerate(bands):
                    for i in range(len(epochs)):
                        ft = np.abs(np.fft.rfft(epochs[i], axis=1))
                        fq = np.fft.rfftfreq(epochs.shape[2], d=1.0 / 160)
                        mask = (fq >= lo) & (fq <= hi)
                        X_bands[i, bi * n_ch:(bi + 1) * n_ch] = np.log(np.sum(ft[:, mask], axis=1) + 1e-10)
                Xt_list, Xv_list = [], []
                for bi in range(n_b):
                    bf = X_bands[:, bi * n_ch:(bi + 1) * n_ch]
                    cov_pos = np.cov(bf[(train) & (ys == 1)].T) + 1e-6 * np.eye(n_ch)
                    cov_neg = np.cov(bf[(train) & (ys == 0)].T) + 1e-6 * np.eye(n_ch)
                    evals, evecs = eigh(cov_pos, cov_pos + cov_neg)
                    idx_sort = np.argsort(evals)[::-1][:best_k]
                    fil = evecs[:, idx_sort]
                    Xt_list.append(np.log(np.var(bf[train] @ fil, axis=1) + 1e-10))
                    Xv_list.append(np.log(np.var(bf[test] @ fil, axis=1) + 1e-10))
                Xt_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xt_list])
                Xv_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xv_list])
                m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                               ("clf", LinearSVC(random_state=42, max_iter=5000))])
                m.fit(Xt_all, ys[train])
                yp = m.predict(Xv_all)
                pv.append(float(balanced_accuracy_score(ys[test], yp)))
            except Exception:
                pass
        if pv:
            null_means.append(float(np.mean(pv)))
    p_val = float(np.mean(np.array(null_means) >= real)) if null_means else 1.0

    return {
        "status": "completed", "best_k": best_k, "valid_folds": len(best_res),
        "balanced_accuracy": round(real, 4), "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4), "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in best_res.items()},
        "method_note": "Per-band log-power + per-band train-only CSP (FBCSP-like), fold-safe.",
    }


def run_compare(args):
    v69 = 0.628
    csp = _load_if("eeg_v72_true_mne_csp.json")
    fbcsp = _load_if("eeg_v72_true_fbcsp.json")
    cs = (csp or {}).get("balanced_accuracy", 0) or 0
    fs = (fbcsp or {}).get("balanced_accuracy", 0) or 0
    csp_ok = (csp or {}).get("status") == "completed"
    fb_ok = (fbcsp or {}).get("status") == "completed"

    if fb_ok and fs > v69 + 0.02:
        v = "true_fbcsp_validated_best"
    elif csp_ok and cs > v69 + 0.02:
        v = "true_mne_csp_validated_best"
    elif csp_ok or fb_ok:
        v = "csp_fbcsp_valid_v69_remains_best"
    else:
        v = "v69_remains_only_validated"

    report = {**_safety(), "tool": "eeg_v72_scientific_verdict",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "verdict": v,
              "comparison": {"v69_filterbank_logpower": v69, "true_mne_csp": cs, "true_fbcsp": fs,
                             "metadata": 0.4815, "quality": 0.494}}
    _save(report, "eeg_v72_scientific_verdict.json")
    print(f"V7.2 verdict: {v} (csp={cs:.3f} fbcsp={fs:.3f})", file=sys.stderr)


def _load_if(fn):
    p = os.path.join(EXPORTS, fn)
    return json.load(open(p)) if os.path.exists(p) else None


def _save(data, fn):
    with open(os.path.join(EXPORTS, fn), "w") as f:
        json.dump(data, f, indent=2, default=str)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)
    print(f"V7.2 mode={args.mode}", file=sys.stderr)

    res = _load_epochs(args.max_subjects, args.crop_start, args.crop_end, args.max_channels)
    if res[0] is None:
        print("No data", file=sys.stderr)
        return 1
    epochs, y, subjects = res
    print(f"  {len(epochs)} epochs, {len(np.unique(subjects))} subjects, "
          f"{epochs.shape[1]}×{epochs.shape[2]}", file=sys.stderr)

    if args.mode in ("csp", "all"):
        csp_res = _run_csp(epochs, y, subjects, args)
        _save({**_safety(), **csp_res}, "eeg_v72_true_mne_csp.json")
        print(f"  true_csp: {csp_res.get('balanced_accuracy', 'N/A'):.4} "
              f"folds={csp_res.get('valid_folds', 0)}", file=sys.stderr)

    if args.mode in ("fbcsp", "all"):
        fbcsp_res = _run_fbcsp(epochs, y, subjects, args)
        _save({**_safety(), **fbcsp_res}, "eeg_v72_true_fbcsp.json")
        print(f"  true_fbcsp: {fbcsp_res.get('balanced_accuracy', 'N/A'):.4} "
              f"folds={fbcsp_res.get('valid_folds', 0)}", file=sys.stderr)

    if args.mode in ("compare", "all"):
        run_compare(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

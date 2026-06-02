"""V7.3 — Fast True CSP/FBCSP Runtime Repair.

16 channels, k=2, 30 permutations, cached epochs.
Goal: produce complete N=15 artifacts that V7.2 couldn't finish.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
CACHE = os.path.join(EXPORTS, "cache")
FIGS = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v73_fast")
    p.add_argument("--mode", default="all", choices=["csp", "fbcsp", "compare", "all"])
    p.add_argument("--max-subjects", type=int, default=15)
    p.add_argument("--permutation-tests", type=int, default=30)
    p.add_argument("--crop-start", type=float, default=1.0)
    p.add_argument("--crop-end", type=float, default=3.5)
    p.add_argument("--max-channels", type=int, default=16)
    p.add_argument("--output-prefix", default="eeg_v73_fast")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_epochs(args):
    cache_fn = f"eeg_v73_epochs_n{args.max_subjects}_ch{args.max_channels}_crop{args.crop_start}_{args.crop_end}.npz"
    cache_path = os.path.join(CACHE, cache_fn)
    if os.path.exists(cache_path):
        d = np.load(cache_path, allow_pickle=True)
        return d["epochs"], d["y"], d["subjects"]

    import mne
    from mne.datasets import eegbci
    subs = list(range(1, min(109, args.max_subjects + 1)))
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
                    ch_ct = min(args.max_channels, len(eeg_ch))
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
                        cs_s, cs_e = int(args.crop_start * 160), int(args.crop_end * 160)
                        if cs_e > cs_s:
                            ep = ep[:, cs_s:cs_e]
                        ep -= ep.mean(axis=1, keepdims=True)
                        ep /= (ep.std(axis=1, keepdims=True) + 1e-8)
                        ep = np.clip(ep, -10, 10)
                        all_ep.append(ep)
                        all_y.append(1.0 if desc == "T1" else 0.0)
                        all_s.append(str(subj))
                del raw
        except Exception:
            continue
    if not all_ep:
        return None, None, None
    epochs_np, y_np, s_np = np.stack(all_ep), np.array(all_y), np.array(all_s)
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(cache_path, epochs=epochs_np, y=y_np, subjects=s_np)
    return epochs_np, y_np, s_np


def _bootstrap_ci(vals, n=2000):
    rng = np.random.default_rng(42)
    v = np.array(vals)
    b = np.array([float(np.mean(rng.choice(v, size=len(v), replace=True))) for _ in range(n)])
    return round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def _csp_fold_scores(epochs, y, subjects):
    from mne.decoding import CSP
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC

    fold_sc = {}
    failures = []
    for ts in np.unique(subjects):
        train, test = subjects != ts, subjects == ts
        if not train.any():
            continue
        try:
            with mne_log_level("ERROR"):
                csp = CSP(n_components=2, reg="ledoit_wolf", transform_into="average_power",
                          log=True, norm_trace=False)
                csp.fit(epochs[train], y[train])
            Xt, Xv = csp.transform(epochs[train]), csp.transform(epochs[test])
            m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                           ("clf", LinearSVC(random_state=42, max_iter=5000))])
            m.fit(Xt, y[train])
            yp = m.predict(Xv)
            fold_sc[ts] = float(balanced_accuracy_score(y[test], yp))
        except Exception as exc:
            failures.append({"subject": ts, "exception": type(exc).__name__, "msg": str(exc)[:200]})
    return fold_sc, failures


class mne_log_level:
    def __init__(self, level):
        self.level = level
    def __enter__(self):
        try:
            import mne
            self.orig = mne.get_log_level()
            mne.set_log_level(self.level)
        except Exception:
            pass
    def __exit__(self, *args):
        try:
            import mne
            mne.set_log_level(self.orig)
        except Exception:
            pass


def run_csp(args):
    print("Fast true MNE CSP (16ch, k=2)...", file=sys.stderr)
    epochs, y, subjects = _load_epochs(args)
    if epochs is None:
        return None

    fold_sc, failures = _csp_fold_scores(epochs, y, subjects)
    valid = {k: v for k, v in fold_sc.items() if v is not None}
    if len(valid) < 5:
        return {"status": "failed", "valid_folds": len(valid), "failures": failures}

    vals = list(valid.values())
    real = float(np.mean(vals))
    ci_l, ci_h = _bootstrap_ci(vals)

    from sklearn.utils import shuffle as sk_shuffle
    nulls = []
    for _ in range(args.permutation_tests):
        ys = sk_shuffle(y, random_state=None)
        fs, _ = _csp_fold_scores(epochs, ys, subjects)
        fv = [v for v in fs.values() if v is not None]
        if len(fv) >= 3:
            nulls.append(float(np.mean(fv)))
    p_val = float(np.mean(np.array(nulls) >= real)) if nulls else 1.0

    res = {
        "status": "completed", "method": "true_mne_csp_fast",
        "api_fix": "Removed verbose from CSP constructor. Used mne.set_log_level(ERROR).",
        "valid_folds": len(valid), "failed_folds": len(failures),
        "balanced_accuracy": round(real, 4), "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4), "n_perm": args.permutation_tests,
        "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in valid.items()},
        "method_note": "True MNE CSP, 16ch, k=2, fold-safe LOSO. V7.3 fast config.",
    }
    _save({**_safety(), **res}, "eeg_v73_fast_true_mne_csp.json")
    print(f"  csp: {real:.3f} [{ci_l:.3f},{ci_h:.3f}] p={p_val:.3f} folds={len(valid)}",
          file=sys.stderr)
    return res


def run_fbcsp(args):
    print("Fast true FBCSP (time-domain + per-band CSP)...", file=sys.stderr)
    epochs, y, subjects = _load_epochs(args)
    if epochs is None:
        return None

    bands = [(8, 12), (12, 16), (16, 24)]
    fold_sc, failures = _fbcsp_fold_scores(epochs, y, subjects, bands)
    valid = {k: v for k, v in fold_sc.items() if v is not None}
    if len(valid) < 5:
        return {"status": "failed", "valid_folds": len(valid), "failures": failures}

    vals = list(valid.values())
    real = float(np.mean(vals))
    ci_l, ci_h = _bootstrap_ci(vals)

    from sklearn.utils import shuffle as sk_shuffle
    nulls = []
    for _ in range(args.permutation_tests):
        ys = sk_shuffle(y, random_state=None)
        fs, _ = _fbcsp_fold_scores(epochs, ys, subjects, bands)
        fv = [v for v in fs.values() if v is not None]
        if len(fv) >= 3:
            nulls.append(float(np.mean(fv)))
    p_val = float(np.mean(np.array(nulls) >= real)) if nulls else 1.0

    res = {
        "status": "completed", "method": "true_time_domain_fbcsp_fast",
        "bands": [f"{lo}-{hi}" for lo, hi in bands],
        "valid_folds": len(valid), "failed_folds": len(failures),
        "balanced_accuracy": round(real, 4), "ci_low": ci_l, "ci_high": ci_h,
        "permutation_p": round(p_val, 4), "n_perm": args.permutation_tests,
        "above_chance": p_val < 0.05,
        "fold_scores": {str(k): round(v, 4) for k, v in valid.items()},
        "method_note": "True FBCSP: per-fold time-domain bandpass + train-only CSP per band.",
    }
    _save({**_safety(), **res}, "eeg_v73_fast_true_fbcsp.json")
    print(f"  fbcsp: {real:.3f} [{ci_l:.3f},{ci_h:.3f}] p={p_val:.3f} folds={len(valid)}",
          file=sys.stderr)
    return res


def _fbcsp_fold_scores(epochs, y, subjects, bands):
    from scipy import signal as sig
    from scipy.linalg import eigh
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC

    sfreq = 160
    n_ch = epochs.shape[1]
    fold_sc = {}
    failures = []

    for ts in np.unique(subjects):
        train, test = subjects != ts, subjects == ts
        if not train.any():
            continue
        try:
            Xt_list, Xv_list = [], []
            for lo, hi in bands:
                # Bandpass filter: butter + sosfiltfilt per epoch
                sos = sig.butter(4, [lo, hi], btype="band", fs=sfreq, output="sos")
                ep_bp = sig.sosfiltfilt(sos, epochs, axis=2)
                # Fit CSP on train band-epochs
                cov_pos = (np.cov(ep_bp[train][(y[train] == 1)].reshape(-1, n_ch).T
                                  if (y[train] == 1).any() else ep_bp[train].reshape(-1, n_ch).T)
                           + 1e-6 * np.eye(n_ch))
                cov_neg = (np.cov(ep_bp[train][(y[train] == 0)].reshape(-1, n_ch).T
                                  if (y[train] == 0).any() else ep_bp[train].reshape(-1, n_ch).T)
                           + 1e-6 * np.eye(n_ch))
                evals, evecs = eigh(cov_pos, cov_pos + cov_neg)
                fil = evecs[:, np.argsort(evals)[::-1][:2]]
                # Transform
                Xt_list.append(np.log(np.var(ep_bp[train] @ fil, axis=1) + 1e-10))
                Xv_list.append(np.log(np.var(ep_bp[test] @ fil, axis=1) + 1e-10))

            Xt_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xt_list])
            Xv_all = np.hstack([a.reshape(-1, 1) if a.ndim == 1 else a for a in Xv_list])
            m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                           ("clf", LinearSVC(random_state=42, max_iter=5000))])
            m.fit(Xt_all, y[train])
            yp = m.predict(Xv_all)
            fold_sc[ts] = float(balanced_accuracy_score(y[test], yp))
        except Exception as exc:
            failures.append({"subject": ts, "exception": type(exc).__name__, "msg": str(exc)[:200]})
    return fold_sc, failures


def run_compare(args):
    v69 = 0.628
    csp = _load_if("eeg_v73_fast_true_mne_csp.json")
    fbcsp = _load_if("eeg_v73_fast_true_fbcsp.json")
    cs = (csp or {}).get("balanced_accuracy", 0) or 0
    fs = (fbcsp or {}).get("balanced_accuracy", 0) or 0
    csp_ok = (csp or {}).get("status") == "completed"
    fb_ok = (fbcsp or {}).get("status") == "completed"

    if fb_ok and fs > v69 + 0.02:
        v = "true_fbcsp_validated_best"
    elif csp_ok and cs > v69 + 0.02:
        v = "true_mne_csp_validated_best"
    elif csp_ok or fb_ok:
        v = "true_csp_valid_but_v69_filterbank_remains_best"
    else:
        v = "v69_filterbank_remains_only_validated"

    _save({**_safety(), "tool": "eeg_v73_scientific_verdict",
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "verdict": v, "comparison": {"v69_filterbank_logpower": v69,
                                        "true_mne_csp": cs, "true_fbcsp": fs,
                                        "metadata": 0.4815, "quality": 0.494}},
          "eeg_v73_scientific_verdict.json")
    print(f"V7.3 verdict: {v} (csp={cs:.3f} fbcsp={fs:.3f})", file=sys.stderr)


def _load_if(fn):
    p = os.path.join(EXPORTS, fn)
    return json.load(open(p)) if os.path.exists(p) else None


def _save(data, fn):
    with open(os.path.join(EXPORTS, fn), "w") as f:
        json.dump(data, f, indent=2, default=str)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)
    print(f"V7.3 mode={args.mode}", file=sys.stderr)

    if args.mode in ("csp", "all"):
        run_csp(args)
    if args.mode in ("fbcsp", "all"):
        run_fbcsp(args)
    if args.mode in ("compare", "all"):
        run_compare(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

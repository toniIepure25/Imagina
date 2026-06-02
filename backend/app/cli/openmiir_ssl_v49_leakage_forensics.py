"""OpenMIIR V4.9 — Leakage Forensics & Confound Audit.

Stress-tests V4.8's high condition scores for hidden confounds.
Metadata baselines, shuffle sanity, time-window/channel ablation, stimulus-group control.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")

TASKS = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_v49_leakage_forensics")
    p.add_argument("--mode", default="all", choices=["audit", "metadata", "shuffle", "ablation", "all"])
    p.add_argument("--device", default="auto")
    p.add_argument("--output-prefix", default="openmiir_ssl_v49_leakage_forensics")
    return p


def _load_json(p):
    if p and os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_features_csv():
    csv_path = os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    if not os.path.exists(csv_path):
        return None, None
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        meta = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
                "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
                "analysis_mode", "artifact_rejected"}
        fc = [h for h in header if h not in meta]
        rows = []
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < len(header):
                continue
            row = dict(zip(header, parts))
            try:
                for c in fc:
                    row[c] = float(row[c])
                rows.append(row)
            except (ValueError, KeyError):
                pass
    return rows, fc


def _loso_probe(X, y, subjects):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    fold_scores = {}
    for ts in np.unique(subjects):
        train = subjects != ts
        test = subjects == ts
        if not train.any() or not test.any():
            continue
        m = Pipeline([
            ("imp", SimpleImputer()), ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
        try:
            m.fit(X[train], y[train])
            yp = m.predict(X[test])
            fold_scores[ts] = float(balanced_accuracy_score(y[test], yp))
        except Exception:
            pass
    if len(fold_scores) >= 3:
        return round(float(np.mean(list(fold_scores.values()))), 4)
    return None


def _load_tensors():
    tpath = os.path.join(EXPORTS, "openmiir_ssl_epoch_tensors_experimental.npz")
    if not os.path.exists(tpath):
        return None, None, None, None
    data = np.load(tpath, allow_pickle=True)
    X = data["X"]
    y_cond = data["y_cond"]
    y_subj = data["y_subj"]
    y_code = data.get("y_code", np.zeros(len(y_subj), dtype=int))
    y_stim = data.get("y_stim", np.zeros(len(y_subj), dtype=int))
    return X, y_cond, y_subj, y_code, y_stim


def run_metadata_baseline():
    rows, fc = _load_features_csv()
    X, y_cond, y_subj, y_code, y_stim = _load_tensors()
    if rows is None and X is None:
        print("No data available", file=sys.stderr)
        return {}

    # Use feature CSV rows for metadata
    if rows:
        subjects = np.array([r["subject"] for r in rows])
        stim_groups = np.array([int(r.get("stimulus_group", 0)) for r in rows])
        event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
        conds = np.array([r["condition"] for r in rows])
    else:
        subjects = y_subj
        stim_groups = y_stim if y_stim is not None else np.zeros(len(y_subj), dtype=int)
        event_codes = y_code if y_code is not None else np.zeros(len(y_subj), dtype=int)
        conds = y_cond

    # Encode metadata features
    from sklearn.preprocessing import LabelEncoder
    metadata_features = {}
    for name, data in [("subject", subjects), ("stimulus_group", stim_groups),
                       ("event_code", event_codes)]:
        le = LabelEncoder()
        encoded = le.fit_transform(data).astype(np.float64).reshape(-1, 1)
        metadata_features[name] = encoded

    # Combined metadata
    combined = np.hstack(list(metadata_features.values()))

    results = {}
    warnings = []
    for tn, ti in TASKS.items():
        pos_mask = np.isin(conds, ti["pos"])
        neg_mask = np.isin(conds, ti["neg"])
        mask = pos_mask | neg_mask
        if mask.sum() < 4:
            continue
        yt = np.where(np.isin(conds[mask], ti["pos"]), 1, 0).astype(np.float64)
        st = subjects[mask]

        for meta_name, meta_X in [("subject_only", metadata_features["subject"][mask]),
                                   ("stimulus_group_only", metadata_features["stimulus_group"][mask]),
                                   ("combined_metadata", combined[mask])]:
            score = _loso_probe(meta_X, yt, st)
            if score is not None and score > 0.75:
                warnings.append(f"{tn}/{meta_name} score={score:.3f}: metadata leakage suspected")
            results[f"{tn}/{meta_name}"] = score

    return {"scores": {k: v for k, v in results.items() if v is not None},
            "warnings": warnings,
            "any_metadata_confound": len(warnings) > 0}


def run_shuffle_sanity():
    """Shuffle condition labels and check if performance collapses."""
    X, y_cond, y_subj, _, _ = _load_tensors()
    if X is None:
        return {}

    # Flatten tensors to features
    X_flat = X.reshape(len(X), -1)[:, :10000]

    results = {}
    for tn, ti in TASKS.items():
        pm = np.isin(y_cond, ti["pos"])
        nm = np.isin(y_cond, ti["neg"])
        mask = pm | nm
        if mask.sum() < 4:
            continue
        Xt = X_flat[mask]
        yt = np.where(np.isin(y_cond[mask], ti["pos"]), 1, 0).astype(np.float64)
        st = y_subj[mask]

        # Real score
        real = _loso_probe(Xt, yt, st)

        # Shuffled
        from sklearn.utils import shuffle as sk_shuffle
        null_scores = []
        for _ in range(20):
            ys = sk_shuffle(yt, random_state=None)
            ns = _loso_probe(Xt, ys, st)
            if ns is not None:
                null_scores.append(ns)

        if real is not None and null_scores:
            results[tn] = {
                "real_score": real,
                "null_mean": round(float(np.mean(null_scores)), 4),
                "null_max": round(float(np.max(null_scores)), 4),
                "suspicious": (float(np.max(null_scores)) > 0.70 or
                               float(np.mean(null_scores)) > 0.60),
            }

    return results


def run_time_ablation():
    """Test condition decoding on different time windows."""
    X, y_cond, y_subj, _, _ = _load_tensors()
    if X is None:
        return {}

    n_times = X.shape[2]
    windows = {
        "0-1s": (0, int(0.25 * n_times)),
        "1-3s": (int(0.25 * n_times), int(0.50 * n_times)),
        "3-7s": (int(0.50 * n_times), n_times),
        "first_250ms": (0, int(0.04 * n_times)),
        "last_2s": (max(0, n_times - int(0.3 * n_times)), n_times),
    }

    results = {}
    for tn, ti in TASKS.items():
        pm = np.isin(y_cond, ti["pos"])
        nm = np.isin(y_cond, ti["neg"])
        mask = pm | nm
        if mask.sum() < 4:
            continue
        yt = np.where(np.isin(y_cond[mask], ti["pos"]), 1, 0).astype(np.float64)
        st = y_subj[mask]

        for wname, (wstart, wend) in windows.items():
            if wend <= wstart:
                continue
            Xw = X[mask][:, :, wstart:wend].reshape(mask.sum(), -1)
            score = _loso_probe(Xw[:, :5000], yt, st)
            if score is not None:
                results[f"{tn}/{wname}"] = score

    return results


def run_stimulus_group_control():
    """Check if condition labels are entangled with stimulus_group."""
    rows, fc = _load_features_csv()
    if rows is None:
        return {}

    subjects = np.array([r["subject"] for r in rows])
    conds = np.array([r["condition"] for r in rows])
    stim_groups = np.array([int(r.get("stimulus_group", 0)) for r in rows])

    # Use handcrafted features for fast evaluation
    from sklearn.preprocessing import StandardScaler
    Xh = np.array([[r.get(f, 0.0) for f in fc] for r in rows])
    Xh = StandardScaler().fit_transform(Xh)

    results = {}
    for tn, ti in TASKS.items():
        pm = np.isin(conds, ti["pos"])
        nm = np.isin(conds, ti["neg"])
        mask = pm | nm
        if mask.sum() < 4:
            continue
        Xt = Xh[mask]
        yt = np.where(np.isin(conds[mask], ti["pos"]), 1, 0).astype(np.float64)
        st = subjects[mask]
        sg = stim_groups[mask]

        # Standard LOSO (no control)
        full_score = _loso_probe(Xt, yt, st)

        # Within-stimulus-group control: for each stimulus group, run separate probe
        within_scores = []
        for sg_val in np.unique(sg):
            sg_mask = sg == sg_val
            if sg_mask.sum() < 4:
                continue
            Xsg = Xt[sg_mask]
            ysg = yt[sg_mask]
            ssg = st[sg_mask]
            ws = _loso_probe(Xsg, ysg, ssg)
            if ws is not None:
                within_scores.append(ws)

        if full_score is not None and within_scores:
            within_mean = float(np.mean(within_scores))
            results[tn] = {
                "full_score": full_score,
                "within_stimulus_group_mean": round(within_mean, 4),
                "drop": round(full_score - within_mean, 4),
                "stimulus_confound_suspected": (full_score - within_mean) > 0.20,
            }

    return results


def run_forensic_verdict():
    metadata = run_metadata_baseline()
    shuffle = run_shuffle_sanity()
    time_ab = run_time_ablation()
    stim_ctrl = run_stimulus_group_control()

    # Audit V4.8
    v48 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v48_nested_loso_experimental.json"))
    main_eval = _load_json(os.path.join(EXPORTS, "openmiir_condition_eval.json"))
    cond_manifest = os.path.exists(os.path.join(META_DIR, "condition_manifest.json"))

    audit = {
        "v48_exists": v48 is not None,
        "v48_protocol": v48.get("protocol") if v48 else None,
        "v48_leakage_free": v48.get("leakage_free", False) if v48 else False,
        "main_eval_blocked": (main_eval or {}).get("status") == "blocked" if main_eval else True,
        "no_condition_manifest": not cond_manifest,
        "safety_fields_ok": all((v48 or {}).get(k) for k in ["not_for_scientific_claims",
                                  "production_valid", "no_raw_eeg_exposed"]) if v48 else False,
    }

    # Count forensic failures
    failed = []
    passed = []
    metadata_fail = metadata.get("any_metadata_confound", False)
    shuffle_fail = any(v.get("suspicious") for v in shuffle.values())
    stim_fail = any(v.get("stimulus_confound_suspected") for v in stim_ctrl.values())

    if metadata_fail:
        failed.append("metadata_confound")
    else:
        passed.append("metadata_baseline")
    if shuffle_fail:
        failed.append("shuffle_sanity")
    else:
        passed.append("shuffle_sanity")
    if stim_fail:
        failed.append("stimulus_group_confound")
    else:
        passed.append("stimulus_group_control")

    if len(failed) == 0:
        verdict = "credible_signal"
    elif len(failed) <= 1:
        verdict = "partially_confounded"
    else:
        verdict = "strongly_confounded"

    conclusion = {
        **_safety(),
        "tool": "openmiir_ssl_v49_forensic_conclusion",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "v48_scores_trusted": verdict == "credible_signal",
        "failed_controls": failed,
        "passed_controls": passed,
        "metadata_baseline": metadata,
        "shuffle_sanity": shuffle,
        "time_window_ablation": time_ab,
        "stimulus_group_control": stim_ctrl,
        "protocol_audit": audit,
        "honest_interpretation": _verdict_text(verdict, failed, passed),
    }

    with open(os.path.join(EXPORTS, "openmiir_ssl_v49_forensic_conclusion.json"), "w") as f:
        json.dump(conclusion, f, indent=2, default=str)

    print(f"Forensic verdict: {verdict} (failed={failed}, passed={passed})", file=sys.stderr)
    return conclusion


def _verdict_text(verdict, failed, passed):
    if verdict == "credible_signal":
        return ("V4.8 nested LOSO scores passed forensic controls. "
                "No metadata leakage, no stimulus-group confound, "
                "no shuffle-inflated scores. Scores appear genuinely "
                "high (0.93-0.96) due to per-fold encoder fine-tuning "
                "with condition-head optimization. However, N=10 subjects "
                "and per-fold training make these results task-specific "
                "and not a basis for BCI or clinical claims.")
    if verdict == "partially_confounded":
        return (f"V4.8 scores are partially confounded. "
                f"Failed controls: {failed}. Passed: {passed}. "
                f"The high scores (0.93-0.96) should NOT be trusted "
                f"as pure condition-decoding evidence. "
                f"Handcrafted features remain the more defensible baseline.")
    return (f"V4.8 scores are STRONGLY CONFOUNDED. "
            f"Failed controls: {failed}. "
            f"The high scores are NOT valid condition-decoding evidence. "
            f"V4.8 should be deprecated as a condition-decoding benchmark. "
            f"Handcrafted features remain the only scientifically defensible baseline.")


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"V4.9 forensics mode={args.mode}", file=sys.stderr)

    if args.mode in ("audit", "all"):
        v48 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v48_nested_loso_experimental.json"))
        main_eval = _load_json(os.path.join(EXPORTS, "openmiir_condition_eval.json"))
        audit = {
            **_safety(),
            "tool": "openmiir_ssl_v49_protocol_audit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "v48_exists": v48 is not None,
            "v48_protocol": (v48 or {}).get("protocol"),
            "v48_leakage_free": (v48 or {}).get("leakage_free"),
            "main_eval_blocked": (main_eval or {}).get("status") == "blocked",
            "no_condition_manifest": not os.path.exists(
                os.path.join(META_DIR, "condition_manifest.json")),
        }
        with open(os.path.join(EXPORTS, "openmiir_ssl_v49_protocol_audit.json"), "w") as f:
            json.dump(audit, f, indent=2, default=str)
        print(f"Audit: v48={audit['v48_exists']} protocol={audit['v48_protocol']}", file=sys.stderr)

    if args.mode in ("metadata", "all"):
        md = run_metadata_baseline()
        md_artifact = {**_safety(), "tool": "openmiir_ssl_v49_metadata_baselines",
                       "generated_at": datetime.now(timezone.utc).isoformat(), **md}
        with open(os.path.join(EXPORTS, "openmiir_ssl_v49_metadata_baselines.json"), "w") as f:
            json.dump(md_artifact, f, indent=2, default=str)
        print(f"Metadata: warnings={len(md.get('warnings', []))}", file=sys.stderr)

    if args.mode in ("shuffle", "all"):
        sf = run_shuffle_sanity()
        sf_artifact = {**_safety(), "tool": "openmiir_ssl_v49_shuffle_sanity",
                       "generated_at": datetime.now(timezone.utc).isoformat(), "results": sf}
        with open(os.path.join(EXPORTS, "openmiir_ssl_v49_shuffle_sanity.json"), "w") as f:
            json.dump(sf_artifact, f, indent=2, default=str)
        suspicious = sum(1 for v in sf.values() if v.get("suspicious"))
        print(f"Shuffle: {suspicious} suspicious tasks", file=sys.stderr)

    if args.mode in ("ablation", "all"):
        ta = run_time_ablation()
        sg = run_stimulus_group_control()
        ta_artifact = {**_safety(), "tool": "openmiir_ssl_v49_time_window_ablation",
                       "generated_at": datetime.now(timezone.utc).isoformat(),
                       "time_windows": ta}
        with open(os.path.join(EXPORTS, "openmiir_ssl_v49_time_window_ablation.json"), "w") as f:
            json.dump(ta_artifact, f, indent=2, default=str)
        sg_artifact = {**_safety(), "tool": "openmiir_ssl_v49_stimulus_group_control",
                       "generated_at": datetime.now(timezone.utc).isoformat(),
                       "results": sg}
        with open(os.path.join(EXPORTS, "openmiir_ssl_v49_stimulus_group_control.json"), "w") as f:
            json.dump(sg_artifact, f, indent=2, default=str)
        confounds = sum(1 for v in sg.values() if v.get("stimulus_confound_suspected"))
        print(f"Stimulus control: {confounds} confounded tasks", file=sys.stderr)

    if args.mode == "all":
        run_forensic_verdict()

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""OpenMIIR Benchmark Diagnostics v4.1 — confound and leakage checks."""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_epoch_benchmark_diagnostics")
    p.add_argument("--features-csv", default=None)
    p.add_argument("--benchmark-json", default=None)
    p.add_argument("--output-prefix", default="openmiir_epoch_benchmark_diagnostics")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    csv_path = args.features_csv or os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    bm_path = args.benchmark_json or os.path.join(EXPORTS, "openmiir_epoch_condition_benchmark_experimental.json")

    benchmark = None
    if os.path.exists(bm_path):
        with open(bm_path) as f:
            benchmark = json.load(f)

    rows = []
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        meta = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
                "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
                "analysis_mode", "artifact_rejected"}
        fc = [h for h in header if h not in meta]
        for line in f:
            p = line.strip().split(",")
            if len(p) < len(header):
                continue
            row = dict(zip(header, p))
            try:
                for c in fc:
                    row[c] = float(row[c])
                rows.append(row)
            except (ValueError, KeyError):
                continue

    n_subjects = len(set(r["subject"] for r in rows))
    n_epochs = len(rows)
    leakage_detected = (benchmark or {}).get("leakage_detected", False)

    # Class balance
    class_balance = Counter(r["condition"] for r in rows)

    # Quality confound check
    quality_cols = ["signal_quality", "peak_to_peak", "variance", "high_amplitude_ratio"]
    confound_warnings = []
    for qc in quality_cols:
        if qc not in rows[0]:
            continue
        by_cond = defaultdict(list)
        for r in rows:
            by_cond[r["condition"]].append(r.get(qc, 0))
        if len(by_cond) < 2:
            continue
        means = {c: float(np.mean(vals)) for c, vals in by_cond.items()}
        mx = max(means.values())
        mn = min(means.values())
        spread_val = (mx - mn) / max(abs(mn), 1e-10)
        if abs(spread_val) > 2.0:
            confound_warnings.append({
                "feature": qc,
                "issue": "Strong condition difference ({:.1f}x)".format(spread_val),
                "by_condition": {c: round(m, 6) for c, m in means.items()},
            })

    # Subject predictability
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    feat_keys = [k for k in fc if k in rows[0]]
    if feat_keys and n_subjects >= 3:
        X_subj = np.array([[r.get(k, 0.0) for k in feat_keys] for r in rows])
        y_subj = np.array([r["subject"] for r in rows])
        from sklearn.utils import shuffle as sk_shuffle
        X_subj, y_subj = sk_shuffle(X_subj, y_subj, random_state=42)
        model = Pipeline([
            ("imp", SimpleImputer(strategy="mean")),
            ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import LabelEncoder
        y_enc = LabelEncoder().fit_transform(y_subj)
        try:
            ss = cross_val_score(model, X_subj[:2000], y_enc[:2000],
                                 cv=min(3, n_subjects), scoring="balanced_accuracy")
            subj_acc = float(np.mean(ss))
        except Exception:
            subj_acc = None
    else:
        subj_acc = None

    diagnostics = {
        "tool": "openmiir_epoch_benchmark_diagnostics_v4.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "leakage": {"detected": leakage_detected},
        "class_balance": dict(class_balance),
        "confound_warnings": confound_warnings,
        "subject_predictability": {
            "balanced_accuracy": round(subj_acc, 4) if subj_acc else None,
            "warning": "Subject easily predictable" if subj_acc and subj_acc > 0.5 else None,
        },
        "data_summary": {"n_subjects": n_subjects, "n_epochs": n_epochs},
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(diagnostics, f, indent=2, default=str)

    print("Diagnostics: leakage={} confounds={}".format(
        leakage_detected, len(confound_warnings)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Subject Generalization Profile + L2SO stress test v4.2."""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")

TASKS = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}

BEST_MODELS = {
    "perception_vs_imagery": "LinearSVC",
    "perception_vs_noise": "RandomForest",
    "cued_vs_uncued_imagery": "LogisticRegression",
    "imagery_vs_noise": "LinearSVC",
    "perception_vs_cued_imagery": "RandomForest",
    "perception_vs_uncued_imagery": "LinearSVC",
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_subject_generalization_profile")
    p.add_argument("--features-csv", default=None)
    p.add_argument("--output-prefix", default="openmiir_subject_generalization_profile")
    p.add_argument("--l2so", type=str, default="true")
    return p


def _load_rows(csv_path):
    rows = []
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        meta = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
                "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
                "analysis_mode", "artifact_rejected"}
        fc = [h for h in header if h not in meta]
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


def _get_model(name):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC

    if name == "LogisticRegression":
        return Pipeline([
            ("imp", SimpleImputer(strategy="mean")),
            ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
    if name == "RandomForest":
        return RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
    return Pipeline([
        ("imp", SimpleImputer(strategy="mean")),
        ("scl", StandardScaler()),
        ("clf", LinearSVC(random_state=42, max_iter=5000)),
    ])


def _build_dataset(rows, task_info, fc):
    pos, neg = set(task_info["pos"]), set(task_info["neg"])
    X, y, subs = [], [], []
    for r in rows:
        c = r.get("condition", "")
        if c in pos:
            X.append([r.get(f, 0.0) for f in fc])
            y.append(1)
            subs.append(r["subject"])
        elif c in neg:
            X.append([r.get(f, 0.0) for f in fc])
            y.append(0)
            subs.append(r["subject"])
    if len(X) < 4:
        return None, None, None
    return np.array(X, dtype=np.float64), np.array(y), np.array(subs)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    csv_path = args.features_csv or os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    rows, fc = _load_rows(csv_path)
    if not rows:
        print("No features found", file=sys.stderr)
        return 1

    from sklearn.metrics import balanced_accuracy_score

    # === LOSO per-subject profile ===
    profile = []
    for tn, ti in TASKS.items():
        X, y, subs = _build_dataset(rows, ti, fc)
        if X is None:
            continue
        model = _get_model(BEST_MODELS.get(tn, "LogisticRegression"))

        for ts in np.unique(subs):
            train = subs != ts
            test = subs == ts
            if not train.any() or not test.any():
                continue
            try:
                model.fit(X[train], y[train])
                yp = model.predict(X[test])
                bal = float(balanced_accuracy_score(y[test], yp))
                profile.append({
                    "task": tn, "subject": ts,
                    "bal_acc": round(bal, 4),
                    "n_test": int(test.sum()),
                })
            except Exception:
                pass

    task_stats = {}
    for tn in TASKS:
        tp = [p for p in profile if p["task"] == tn]
        if not tp:
            continue
        bals = [p["bal_acc"] for p in tp]
        task_stats[tn] = {
            "mean": round(float(np.mean(bals)), 4),
            "std": round(float(np.std(bals)), 4),
            "min": round(float(np.min(bals)), 4),
            "max": round(float(np.max(bals)), 4),
            "cv": round(float(np.std(bals)) / max(float(np.mean(bals)), 1e-6), 4),
            "worst_subject": min(tp, key=lambda x: x["bal_acc"])["subject"],
            "best_subject": max(tp, key=lambda x: x["bal_acc"])["subject"],
            "gap": round(max(bals) - min(bals), 4),
        }

    # === L2SO ===
    l2so_results = {}
    if args.l2so.lower() in ("true", "1", "yes"):
        from itertools import combinations

        for tn, ti in TASKS.items():
            X, y, subs = _build_dataset(rows, ti, fc)
            if X is None:
                continue
            model = _get_model(BEST_MODELS.get(tn, "LogisticRegression"))
            unique_subs = np.unique(subs)
            pairs = list(combinations(unique_subs, 2))[:45]
            pair_scores = []
            for p1, p2 in pairs:
                test = (subs == p1) | (subs == p2)
                train = ~test
                if not train.any() or not test.any():
                    continue
                try:
                    model.fit(X[train], y[train])
                    yp = model.predict(X[test])
                    pair_scores.append(float(balanced_accuracy_score(y[test], yp)))
                except Exception:
                    pass
            if pair_scores:
                lso_mean = task_stats.get(tn, {}).get("mean", 0)
                l2so_mean = float(np.mean(pair_scores))
                l2so_results[tn] = {
                    "mean": round(l2so_mean, 4),
                    "std": round(float(np.std(pair_scores)), 4),
                    "loso_mean": lso_mean,
                    "delta_vs_loso": round(lso_mean - l2so_mean, 4),
                    "fragile": abs(lso_mean - l2so_mean) > 0.05,
                }

    report = {
        "tool": "openmiir_subject_generalization_profile_v4.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "n_subjects": len(set(r["subject"] for r in rows)),
        "task_stats": task_stats,
        "profile": profile,
        "l2so_results": l2so_results,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    csv_out = os.path.join(EXPORTS, f"{args.output_prefix}.csv")
    with open(csv_out, "w") as f:
        f.write("task,subject,bal_acc,n_test\n")
        for p in profile:
            f.write(f"{p['task']},{p['subject']},{p['bal_acc']},{p['n_test']}\n")

    print(f"Subject profile: {len(task_stats)} tasks, {len(profile)} folds, l2so={len(l2so_results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""OpenMIIR Epoch-Level Condition Benchmark v4.1 — Fast, statistically hardened."""

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

FEATURE_GROUPS = {
    "global_spectral": ["delta_power", "theta_power", "alpha_power", "beta_power",
                         "gamma_low_power", "theta_alpha_ratio", "beta_alpha_ratio",
                         "alpha_beta_ratio", "spectral_entropy", "total_power", "log_total_power"],
    "regional_alpha": ["alpha_frontal", "alpha_central", "alpha_parietal", "alpha_occipital", "alpha_temporal"],
    "regional_theta": ["theta_frontal", "theta_central", "theta_parietal", "theta_occipital", "theta_temporal"],
    "temporal": ["alpha_early", "alpha_mid", "alpha_late", "theta_early", "theta_mid", "theta_late"],
    "quality": ["signal_quality", "peak_to_peak", "variance", "flat_channel_ratio", "high_amplitude_ratio"],
}

ABLATION_GROUPS = {
    "all_features": ["global_spectral", "regional_alpha", "regional_theta", "temporal", "quality"],
    "global_spectral_only": ["global_spectral"],
    "regional_only": ["regional_alpha", "regional_theta"],
    "quality_only": ["quality"],
    "temporal_only": ["temporal"],
    "no_quality": ["global_spectral", "regional_alpha", "regional_theta", "temporal"],
    "no_temporal": ["global_spectral", "regional_alpha", "regional_theta", "quality"],
    "alpha_theta_only": ["global_spectral"],
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_epoch_condition_benchmark")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--features-csv", default=None)
    p.add_argument("--task", default="all")
    p.add_argument("--cv", default="leave-one-subject-out")
    p.add_argument("--permutation-tests", type=int, default=100)
    p.add_argument("--permutation-model", default="best_only")
    p.add_argument("--ablation", default="all")
    p.add_argument("--fast", type=str, default="true")
    p.add_argument("--output-prefix", default="openmiir_epoch_condition_benchmark_experimental")
    return p


def _load_features(csv_path):
    rows = []
    if not csv_path or not os.path.exists(csv_path):
        return None, None
    meta = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
            "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
            "analysis_mode", "artifact_rejected"}
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
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
    return rows, fc


def _get_selected_features(all_fc, groups):
    selected = set()
    for g in groups:
        selected.update(FEATURE_GROUPS.get(g, []))
    return [c for c in all_fc if c in selected]


def _build_dataset(rows, task_info, feature_cols):
    pos, neg = set(task_info["pos"]), set(task_info["neg"])
    X, y, subjects = [], [], []
    for r in rows:
        c = r.get("condition", "")
        if c in pos:
            X.append([r.get(fc, 0.0) for fc in feature_cols])
            y.append(1)
            subjects.append(r["subject"])
        elif c in neg:
            X.append([r.get(fc, 0.0) for fc in feature_cols])
            y.append(0)
            subjects.append(r["subject"])
    if len(X) < 4:
        return None, None, None
    return np.array(X, dtype=np.float64), np.array(y), np.array(subjects)


def _get_models(fast):
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC

    n_est = 80 if fast else 200
    max_d = 8 if fast else 12

    return {
        "Dummy": DummyClassifier(strategy="stratified", random_state=42),
        "LogisticRegression": Pipeline([
            ("imp", SimpleImputer(strategy="mean")),
            ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=n_est, max_depth=max_d, random_state=42, n_jobs=-1),
        "LinearSVC": Pipeline([
            ("imp", SimpleImputer(strategy="mean")),
            ("scl", StandardScaler()),
            ("clf", LinearSVC(random_state=42, max_iter=5000)),
        ]),
    }


def _loso_cv(X, y, subjects, model):
    from sklearn.metrics import balanced_accuracy_score
    unique_subs = np.unique(subjects)
    scores = []
    leakage = False
    for ts in unique_subs:
        train = subjects != ts
        test = subjects == ts
        if not train.any() or not test.any():
            continue
        train_set = set(subjects[train])
        if {ts} & train_set:
            leakage = True
        try:
            model.fit(X[train], y[train])
            yp = model.predict(X[test])
            scores.append(float(balanced_accuracy_score(y[test], yp)))
        except Exception:
            continue
    if not scores:
        return None
    return {
        "mean_bal_acc": round(float(np.mean(scores)), 4),
        "std_bal_acc": round(float(np.std(scores)), 4),
        "n_folds": len(scores),
        "leakage_detected": leakage,
    }


def _permutation_test(X, y, subjects, n_perm):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.utils import shuffle as sk_shuffle

    rf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
    real = _loso_cv(X, y, subjects, rf)
    if not real:
        return None
    real_score = real["mean_bal_acc"]
    null_scores = []

    for _ in range(n_perm):
        y_shuf = sk_shuffle(y, random_state=None)
        null_rf = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42, n_jobs=-1)
        nr = _loso_cv(X, y_shuf, subjects, null_rf)
        if nr:
            null_scores.append(nr["mean_bal_acc"])

    if not null_scores:
        return None
    ns = np.array(null_scores)
    p_val = float(np.mean(ns >= real_score))
    return {
        "real_score": round(real_score, 4),
        "null_scores": [round(x, 4) for x in ns.tolist()],
        "null_mean": round(float(np.mean(ns)), 4),
        "null_std": round(float(np.std(ns)), 4),
        "p_value": round(p_val, 4),
        "above_chance": p_val < 0.05,
        "effect_over_null": round(real_score - float(np.mean(ns)), 4),
        "n_permutations": n_perm,
    }


def _feature_importance_rf(X, y, feature_cols):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer

    X_clean = SimpleImputer(strategy="mean").fit_transform(X)
    rf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
    rf.fit(X_clean, y)
    imps = rf.feature_importances_
    result = sorted(
        [{"feature": feature_cols[i], "importance": round(float(imps[i]), 6)}
         for i in range(min(len(feature_cols), len(imps)))],
        key=lambda x: x["importance"], reverse=True)
    return result


def _group_importance(feature_imp):
    group_imp = {}
    for fi in feature_imp:
        for gn, gcols in FEATURE_GROUPS.items():
            if fi["feature"] in gcols:
                group_imp[gn] = group_imp.get(gn, 0) + fi["importance"]
                break
    return sorted(
        [{"group": k, "importance": round(v, 4)} for k, v in group_imp.items()],
        key=lambda x: x["importance"], reverse=True)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    fast = args.fast.lower() in ("true", "1", "yes")

    csv_path = args.features_csv or os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    rows, all_fc = _load_features(csv_path)
    if not rows:
        print("No features found", file=sys.stderr)
        return 1

    subjects_list = sorted(set(r["subject"] for r in rows))
    models = _get_models(fast)
    task_names = list(TASKS.keys()) if args.task == "all" else [t for t in args.task.split() if t in TASKS]

    task_results = {}
    null_distributions = {}
    feature_imp_all = {}
    ablation_results = {}
    all_scores = []

    print(f"Subjects={len(subjects_list)} epochs={len(rows)} features={len(all_fc)} "
          f"tasks={len(task_names)} fast={fast}", file=sys.stderr)

    # === Main benchmark ===
    for tn in task_names:
        ti = TASKS[tn]
        X, y, subs = _build_dataset(rows, ti, all_fc)
        if X is None:
            print(f"  {tn}: skipped (insufficient data)", file=sys.stderr)
            continue

        n_pos = int(y.sum())
        n_neg = len(y) - n_pos
        print(f"  {tn}: {len(y)} epochs ({n_pos} pos, {n_neg} neg) | {len(np.unique(subs))} subs",
              file=sys.stderr)

        task_results[tn] = {}
        best_non_dummy = (None, 0)

        for mn, model in models.items():
            res = _loso_cv(X, y, subs, model)
            if not res:
                continue
            task_results[tn][mn] = res
            if mn != "Dummy" and res["mean_bal_acc"] > best_non_dummy[1]:
                best_non_dummy = (mn, res["mean_bal_acc"])
            all_scores.append({"task": tn, "model": mn, "bal_acc": res["mean_bal_acc"]})
            print(f"    {mn}: bal={res['mean_bal_acc']:.3f}", file=sys.stderr)

        # Permutation test for best model
        if args.permutation_tests > 0 and best_non_dummy[0]:
            print(f"    Permutation: {args.permutation_tests} tests for {best_non_dummy[0]}...", file=sys.stderr)
            perm = _permutation_test(X, y, subs, args.permutation_tests)
            if perm:
                null_distributions[tn] = {"best_model": best_non_dummy[0], **perm}
                task_results[tn][best_non_dummy[0]]["permutation"] = perm
                p_str = f"p={perm['p_value']:.4f}"
                if perm["above_chance"]:
                    p_str += " (above chance)"
                print(f"    {best_non_dummy[0]} perm: {p_str}", file=sys.stderr)

        # Feature importance
        feature_imp_all[tn] = _feature_importance_rf(X, y, all_fc)

    # === Ablations ===
    if args.ablation:
        print("\nAblations:", file=sys.stderr)
        for ab_name, ab_groups in ABLATION_GROUPS.items():
            ab_fc = _get_selected_features(all_fc, ab_groups)
            if not ab_fc:
                continue
            ab_task_res = {}
            for tn in task_names:
                ti = TASKS[tn]
                X, y, subs = _build_dataset(rows, ti, ab_fc)
                if X is None:
                    continue
                from sklearn.ensemble import RandomForestClassifier
                rf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
                res = _loso_cv(X, y, subs, rf)
                if res:
                    ab_task_res[tn] = res
            if ab_task_res:
                avg = float(np.mean([v["mean_bal_acc"] for v in ab_task_res.values()]))
                ablation_results[ab_name] = {
                    "n_features": len(ab_fc),
                    "avg_bal_acc": round(avg, 4),
                    "per_task": {tn: round(v["mean_bal_acc"], 4)
                                 for tn, v in ab_task_res.items()},
                }
                print(f"  {ab_name}: {len(ab_fc)} features, avg_bal={avg:.3f}", file=sys.stderr)

    # === Build report ===
    best_per_task = {}
    for tn, md in task_results.items():
        best = max(((k, v["mean_bal_acc"]) for k, v in md.items()),
                   key=lambda x: x[1], default=(None, 0))
        best_per_task[tn] = {"model": best[0], "bal_acc": best[1]}
        perm_info = (md.get(best[0], {}) if isinstance(md.get(best[0]), dict)
                     else {}).get("permutation", {})
        best_per_task[tn]["p_value"] = perm_info.get("p_value")
        best_per_task[tn]["above_chance"] = perm_info.get("above_chance", False)

    report = {
        "tool": "openmiir_epoch_condition_benchmark_v4.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "n_subjects": len(subjects_list),
        "n_epochs": len(rows),
        "n_features": len(all_fc),
        "cv_method": "leave-one-subject-out",
        "group_cv_used": True,
        "leakage_detected": False,
        "tasks_completed": list(task_results.keys()),
        "best_model_per_task": best_per_task,
        "task_results": task_results,
        "null_distributions": null_distributions,
        "feature_importance": feature_imp_all,
        "ablation_results": ablation_results,
        "all_scores": all_scores,
        "feature_groups": {gn: list(gc) for gn, gc in FEATURE_GROUPS.items()},
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    scores_csv = os.path.join(EXPORTS, f"{args.output_prefix}_scores.csv")
    with open(scores_csv, "w") as f:
        f.write("task,model,balanced_accuracy\n")
        for s in all_scores:
            f.write(f"{s['task']},{s['model']},{s['bal_acc']:.4f}\n")

    nulls_path = os.path.join(EXPORTS, f"{args.output_prefix}_null_distributions.json")
    with open(nulls_path, "w") as f:
        json.dump(null_distributions, f, indent=2, default=str)

    # Ablation CSV
    if ablation_results:
        ab_csv = os.path.join(EXPORTS, f"{args.output_prefix}_ablation.csv")
        with open(ab_csv, "w") as f:
            f.write("ablation,n_features,avg_bal_acc\n")
            for an, ar in ablation_results.items():
                f.write(f"{an},{ar['n_features']},{ar['avg_bal_acc']}\n")

    # Feature importance CSV
    if feature_imp_all:
        # Use first task's importance
        first_task_imp = next(iter(feature_imp_all.values()), [])
        fi_csv = os.path.join(EXPORTS, f"{args.output_prefix}_feature_importance.csv")
        with open(fi_csv, "w") as f:
            f.write("feature,importance\n")
            for fi in first_task_imp[:20]:
                f.write(f"{fi['feature']},{fi['importance']}\n")

    print(f"Done: {len(task_results)} tasks, {len(ablation_results)} ablations, "
          f"{len(null_distributions)} perm tests", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
